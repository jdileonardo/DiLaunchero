package com.jdileonardo.dilaunchero

import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.provider.Settings
import android.view.KeyEvent
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.focusable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asAndroidBitmap
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.key.onPreviewKeyEvent
import app.rive.Fit
import app.rive.ImageAsset
import app.rive.Rive
import app.rive.RiveFile
import app.rive.RiveFileSource
import app.rive.ViewModelInstance
import app.rive.ViewModelSource
import app.rive.rememberRiveFile
import app.rive.rememberRiveWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import app.rive.Result as RiveResult

/*
 * The launcher drawn by Rive (res/raw/home.riv, built from rive-ui/).
 *
 * Rive only draws. This file owns the state: it loads apps, tracks focus from the remote and
 * writes everything into the file's "Home" view model. Property names below match
 * rive-ui/tools/gen_data.py.
 */

private const val APP_COLUMNS = 8
/** Grid rows that fit in the apps window below the favourites, and their height in artboard points. */
private const val APP_ROWS_VISIBLE = 3
private const val APP_ROW_HEIGHT = 182f

/** The Rive designs the home screen can wear; each is a theme folder in rive-ui/themes/. */
internal enum class LauncherTheme(val label: String, val raw: Int, val background: Color) {
  DEFAULT("Default", R.raw.home_vanilla, Color(0xFF0A0F1C)),
  RETRO("Retro", R.raw.home_retro, Color(0xFFF3E2BF)),
  SCOPA("Scopa", R.raw.home_scopa, Color(0xFF0C3A20)),
}

private enum class TopItem(val prop: String) {
  PREV("prevFocused"), PLAY("playFocused"), NEXT("nextFocused"),
  SCREENSAVER("screensaverFocused"), SETTINGS("settingsFocused"),
  /** the palette button under the gear; not in the left/right row, reached with down from Settings */
  THEME("themeFocused"),
}

private enum class SettingsMenu { NONE, MAIN, THEME }

private sealed interface Focus {
  data class Top(val item: TopItem) : Focus
  data class Fav(val index: Int) : Focus
  data class App(val index: Int) : Focus
}

/** One tile's view model instance plus the decoded icon it shows. */
private class Tile(val vmi: ViewModelInstance, val icon: ImageAsset?) {
  fun close() { vmi.close(); icon?.close() }
}

@Composable
internal fun MainActivity.RiveLauncherScreen() {
  val prefs = remember { getSharedPreferences("launcher", android.content.Context.MODE_PRIVATE) }
  var theme by remember {
    mutableStateOf(LauncherTheme.entries.firstOrNull { it.name == prefs.getString("theme", null) } ?: LauncherTheme.DEFAULT)
  }
  // a new theme is a new file and view model, so start the screen afresh
  key(theme) {
    RiveHome(theme) { picked ->
      prefs.edit().putString("theme", picked.name).apply()
      theme = picked
    }
  }
}

/** One theme's home screen. Settings opens a menu: Android settings, or launcher settings (theme). */
@Composable
private fun MainActivity.RiveHome(theme: LauncherTheme, onPickTheme: (LauncherTheme) -> Unit) {
  val worker = rememberRiveWorker()
  val fileResult = rememberRiveFile(RiveFileSource.RawRes.from(theme.raw), worker)
  val file = (fileResult as? RiveResult.Success)?.value
  if (file == null) {
    Box(Modifier.fillMaxSize().background(theme.background))
    return
  }

  // ---- the Home view model instance -------------------------------------------------------
  var home by remember(file) { mutableStateOf<ViewModelInstance?>(null) }
  LaunchedEffect(file) {
    home = ViewModelInstance.create(file, ViewModelSource.Named("Home").defaultInstance())
  }
  DisposableEffect(home) { val h = home; onDispose { h?.close() } }

  // ---- launcher state (same prefs as the Compose UI, so favourites and order carry over) ----
  var apps by remember { mutableStateOf<List<AppEntry>>(emptyList()) }
  LaunchedEffect(refresh) { apps = withContext(Dispatchers.Default) { loadApps() } }

  val prefs = remember { getSharedPreferences("launcher", android.content.Context.MODE_PRIVATE) }
  var favs by remember { mutableStateOf(prefs.getStringSet("favs", emptySet()) ?: emptySet()) }
  var order by remember {
    mutableStateOf(prefs.getString("app_order", "")!!.split('\n').filter { it.isNotEmpty() })
  }
  val orderedApps = remember(apps, order) {
    val positions = order.withIndex().associate { it.value to it.index }
    apps.sortedWith(compareBy<AppEntry> { positions[it.pkg] ?: Int.MAX_VALUE }.thenBy { it.label.lowercase() })
  }
  val favApps = orderedApps.filter { it.pkg in favs }
  val otherApps = orderedApps.filter { it.pkg !in favs }

  var playing by remember { mutableStateOf<NowPlaying?>(null) }
  LaunchedEffect(Unit) {
    while (true) { playing = withContext(Dispatchers.Default) { queryNowPlaying() }; delay(2_000) }
  }

  var focus by remember { mutableStateOf<Focus?>(null) }
  var menuApp by remember { mutableStateOf<AppEntry?>(null) }
  var settingsMenu by remember { mutableStateOf(SettingsMenu.NONE) }
  var movingPkg by remember { mutableStateOf<String?>(null) }
  var orderBeforeMove by remember { mutableStateOf<List<String>>(emptyList()) }

  val topItems = buildList {
    playing?.let { np ->
      if (np.canPrevious) add(TopItem.PREV)
      if (np.canToggle) add(TopItem.PLAY)
      if (np.canNext) add(TopItem.NEXT)
    }
    add(TopItem.SCREENSAVER); add(TopItem.SETTINGS)
  }

  // Keep focus valid as lists change; start on the first favourite.
  LaunchedEffect(favApps.size, otherApps.size, topItems) {
    if (apps.isEmpty()) return@LaunchedEffect // still loading: wait, or focus lands on Settings
    focus = when (val f = focus) {
      null -> if (favApps.isNotEmpty()) Focus.Fav(0) else if (otherApps.isNotEmpty()) Focus.App(0) else Focus.Top(TopItem.SETTINGS)
      is Focus.Fav -> if (favApps.isEmpty()) Focus.Top(TopItem.SETTINGS) else Focus.Fav(f.index.coerceAtMost(favApps.lastIndex))
      is Focus.App -> if (otherApps.isEmpty()) Focus.Top(TopItem.SETTINGS) else Focus.App(f.index.coerceAtMost(otherApps.lastIndex))
      is Focus.Top -> if (f.item in topItems || f.item == TopItem.THEME) f else Focus.Top(TopItem.SCREENSAVER)
    }
  }

  // ---- push: tiles ------------------------------------------------------------------------
  // One instance per app per section, cached so focus changes are a single property write.
  val favTiles = remember(file) { HashMap<String, Tile>() }
  val appTiles = remember(file) { HashMap<String, Tile>() }
  DisposableEffect(file) { onDispose { (favTiles.values + appTiles.values).forEach { it.close() }; favTiles.clear(); appTiles.clear() } }

  suspend fun tileFor(cache: HashMap<String, Tile>, viewModel: String, app: AppEntry, rf: RiveFile): Tile =
    cache[app.pkg] ?: run {
      val vmi = ViewModelInstance.create(rf, ViewModelSource.Named(viewModel).blankInstance())
      val png = withContext(Dispatchers.IO) { runCatching { icon(app.pkg).toPng() }.getOrNull() }
      val img = png?.let { runCatching { ImageAsset.create(worker, it) }.getOrNull() }
      vmi.setString("label", app.label)
      img?.let { vmi.setImage("icon", it) }
      Tile(vmi, img).also { cache[app.pkg] = it }
    }

  val favKey = favApps.map { it.pkg }
  val appKey = otherApps.map { it.pkg }
  var tilesReady by remember { mutableStateOf(0) }
  LaunchedEffect(home, favKey, appKey) {
    val h = home ?: return@LaunchedEffect
    suspend fun fill(list: String, cache: HashMap<String, Tile>, vm: String, entries: List<AppEntry>) {
      val tiles = entries.map { tileFor(cache, vm, it, file) }
      repeat(h.getListSize(list)) { h.removeFromListAtIndex(list, 0) }
      tiles.forEach { h.appendToList(list, it.vmi) }
    }
    fill("favourites", favTiles, "FavTile", favApps)
    fill("apps", appTiles, "AppTile", otherApps)
    tilesReady++
  }

  // ---- push: focus ------------------------------------------------------------------------
  LaunchedEffect(home, focus, tilesReady, favKey, appKey) {
    val h = home ?: return@LaunchedEffect
    val f = focus
    TopItem.entries.forEach { h.setBoolean(it.prop, f is Focus.Top && f.item == it) }
    favApps.forEachIndexed { i, a -> favTiles[a.pkg]?.vmi?.setBoolean("focused", f is Focus.Fav && f.index == i) }
    otherApps.forEachIndexed { i, a -> appTiles[a.pkg]?.vmi?.setBoolean("focused", f is Focus.App && f.index == i) }
  }

  // ---- push: grid scroll ------------------------------------------------------------------
  // Keep the focused row inside the visible window; Rive eases the grid to the new offset.
  var firstRow by remember { mutableStateOf(0) }
  LaunchedEffect(home, focus, otherApps.size) {
    val h = home ?: return@LaunchedEffect
    val totalRows = (otherApps.size + APP_COLUMNS - 1) / APP_COLUMNS
    val maxFirst = (totalRows - APP_ROWS_VISIBLE).coerceAtLeast(0)
    firstRow = when (val f = focus) {
      is Focus.App -> {
        val row = f.index / APP_COLUMNS
        when {
          row < firstRow -> row
          row >= firstRow + APP_ROWS_VISIBLE -> row - APP_ROWS_VISIBLE + 1
          else -> firstRow
        }
      }
      else -> 0 // back at the top whenever focus leaves the grid
    }.coerceIn(0, maxFirst)
    h.setNumber("appsScroll", -firstRow * APP_ROW_HEIGHT)
    h.setBoolean("appsMoreBelow", firstRow < maxFirst)
  }

  // ---- push: clock, now playing --------------------------------------------------
  LaunchedEffect(home) {
    val h = home ?: return@LaunchedEffect
    val time = SimpleDateFormat("h:mm a", Locale.getDefault())
    val date = SimpleDateFormat("EEEE, MMMM d", Locale.getDefault())
    while (true) {
      val now = Date()
      h.setString("time", time.format(now))
      h.setString("date", date.format(now))
      delay(15_000)
    }
  }

  var artAsset by remember { mutableStateOf<ImageAsset?>(null) }
  var artSource by remember { mutableStateOf<ImageBitmap?>(null) }
  DisposableEffect(Unit) { onDispose { artAsset?.close() } } // runs once, on leaving the screen
  LaunchedEffect(home, playing) {
    val h = home ?: return@LaunchedEffect
    val np = playing
    h.setBoolean("npVisible", np != null)
    if (np == null) return@LaunchedEffect
    h.setString("npTitle", np.title ?: np.app)
    h.setString("npSubtitle", listOfNotNull(np.artist, np.app).joinToString(" · "))
    h.setBoolean("npPlaying", np.playing)
    if (np.art !== artSource) {
      artSource = np.art
      val png = np.art?.let { withContext(Dispatchers.IO) { it.toPng() } }
      val img = png?.let { runCatching { ImageAsset.create(worker, it) }.getOrNull() }
      h.setImage("npArt", img)
      artAsset?.close()
      artAsset = img
    }
  }

  // ---- remote ---------------------------------------------------------------------------
  fun focusedApp(): AppEntry? = when (val f = focus) {
    is Focus.Fav -> favApps.getOrNull(f.index)
    is Focus.App -> otherApps.getOrNull(f.index)
    else -> null
  }

  fun activate() {
    when (val f = focus) {
      is Focus.Top -> when (f.item) {
        TopItem.PREV -> runCatching { mediaController?.transportControls?.skipToPrevious() }
        TopItem.NEXT -> runCatching { mediaController?.transportControls?.skipToNext() }
        TopItem.PLAY -> playing?.let { np ->
          runCatching {
            if (np.playing) mediaController?.transportControls?.pause() else mediaController?.transportControls?.play()
          }
          playing = np.copy(playing = !np.playing)
        }
        TopItem.SCREENSAVER -> startScreensaver()
        TopItem.SETTINGS -> settingsMenu = SettingsMenu.MAIN
        TopItem.THEME -> settingsMenu = SettingsMenu.THEME
      }
      else -> focusedApp()?.let { launch(it.intent) }
    }
  }

  fun move(direction: Int) {
    val pkg = movingPkg ?: return
    val inFav = pkg in favs
    val section = if (inFav) favApps else otherApps
    val index = section.indexOfFirst { it.pkg == pkg }
    if (index < 0) return
    val target = (index + direction).coerceIn(0, section.lastIndex)
    if (target == index) return
    val changed = section.map { it.pkg }.toMutableList()
    changed.add(target, changed.removeAt(index))
    order = if (inFav) changed + otherApps.map { it.pkg } else favApps.map { it.pkg } + changed
    focus = if (inFav) Focus.Fav(target) else Focus.App(target)
  }

  fun finishMove(save: Boolean) {
    if (save) prefs.edit().putString("app_order", order.joinToString("\n")).apply() else order = orderBeforeMove
    val pkg = movingPkg
    movingPkg = null
    if (!save && pkg != null) {
      val fi = favApps.indexOfFirst { it.pkg == pkg }
      val ai = otherApps.indexOfFirst { it.pkg == pkg }
      if (fi >= 0) focus = Focus.Fav(fi) else if (ai >= 0) focus = Focus.App(ai)
    }
  }

  fun navigate(keyCode: Int): Boolean {
    val f = focus ?: return false
    val next: Focus? = when (f) {
      is Focus.Top -> if (f.item == TopItem.THEME) when (keyCode) {
        KeyEvent.KEYCODE_DPAD_UP -> Focus.Top(TopItem.SETTINGS)
        KeyEvent.KEYCODE_DPAD_LEFT -> Focus.Top(TopItem.SCREENSAVER)
        KeyEvent.KEYCODE_DPAD_DOWN ->
          if (favApps.isNotEmpty()) Focus.Fav(favApps.lastIndex) else if (otherApps.isNotEmpty()) Focus.App(0) else null
        else -> null
      } else {
        val i = topItems.indexOf(f.item)
        when (keyCode) {
          KeyEvent.KEYCODE_DPAD_LEFT -> topItems.getOrNull(i - 1)?.let { Focus.Top(it) }
          KeyEvent.KEYCODE_DPAD_RIGHT -> topItems.getOrNull(i + 1)?.let { Focus.Top(it) }
          KeyEvent.KEYCODE_DPAD_DOWN -> when {
            f.item == TopItem.SETTINGS -> Focus.Top(TopItem.THEME)
            favApps.isNotEmpty() -> Focus.Fav(favApps.size / 2)
            otherApps.isNotEmpty() -> Focus.App(0)
            else -> null
          }
          else -> null
        }
      }
      is Focus.Fav -> when (keyCode) {
        KeyEvent.KEYCODE_DPAD_LEFT -> if (f.index > 0) Focus.Fav(f.index - 1) else null
        KeyEvent.KEYCODE_DPAD_RIGHT -> if (f.index < favApps.lastIndex) Focus.Fav(f.index + 1) else null
        KeyEvent.KEYCODE_DPAD_UP -> Focus.Top(if (TopItem.PLAY in topItems) TopItem.PLAY else TopItem.SCREENSAVER)
        KeyEvent.KEYCODE_DPAD_DOWN -> if (otherApps.isEmpty()) null else {
          // favourites are centred above the grid: drop to the column underneath
          val col = (((f.index + 0.5f) / favApps.size) * APP_COLUMNS).toInt()
          Focus.App(col.coerceAtMost(otherApps.lastIndex))
        }
        else -> null
      }
      is Focus.App -> when (keyCode) {
        KeyEvent.KEYCODE_DPAD_LEFT -> if (f.index > 0) Focus.App(f.index - 1) else null
        KeyEvent.KEYCODE_DPAD_RIGHT -> if (f.index < otherApps.lastIndex) Focus.App(f.index + 1) else null
        KeyEvent.KEYCODE_DPAD_DOWN -> if (f.index + APP_COLUMNS <= otherApps.lastIndex) Focus.App(f.index + APP_COLUMNS) else null
        KeyEvent.KEYCODE_DPAD_UP -> when {
          f.index >= APP_COLUMNS -> Focus.App(f.index - APP_COLUMNS)
          favApps.isNotEmpty() -> {
            val col = f.index % APP_COLUMNS
            Focus.Fav((((col + 0.5f) / APP_COLUMNS) * favApps.size).toInt().coerceAtMost(favApps.lastIndex))
          }
          else -> Focus.Top(TopItem.SCREENSAVER)
        }
        else -> null
      }
    }
    if (next != null) focus = next
    return true
  }

  val keyFocus = remember { FocusRequester() }
  LaunchedEffect(menuApp, settingsMenu, home) { if (menuApp == null && settingsMenu == SettingsMenu.NONE) runCatching { keyFocus.requestFocus() } }
  var okDown by remember { mutableStateOf(false) }
  var longPressed by remember { mutableStateOf(false) }

  BackHandler(enabled = true) { if (movingPkg != null) finishMove(false) }

  Box(
    Modifier.fillMaxSize().background(theme.background)
      .focusRequester(keyFocus)
      .focusable()
      .onPreviewKeyEvent { event ->
        val key = event.nativeKeyEvent
        val isOk = key.keyCode == KeyEvent.KEYCODE_DPAD_CENTER || key.keyCode == KeyEvent.KEYCODE_ENTER ||
          key.keyCode == KeyEvent.KEYCODE_BUTTON_A
        if (movingPkg != null) {
          if (key.action != KeyEvent.ACTION_DOWN) return@onPreviewKeyEvent isOk
          val inFav = movingPkg in favs
          when (key.keyCode) {
            KeyEvent.KEYCODE_DPAD_LEFT -> move(-1)
            KeyEvent.KEYCODE_DPAD_RIGHT -> move(1)
            KeyEvent.KEYCODE_DPAD_UP -> if (!inFav) move(-APP_COLUMNS)
            KeyEvent.KEYCODE_DPAD_DOWN -> if (!inFav) move(APP_COLUMNS)
            KeyEvent.KEYCODE_BUTTON_B -> finishMove(false)
            else -> if (isOk && key.repeatCount == 0) finishMove(true) else return@onPreviewKeyEvent false
          }
          return@onPreviewKeyEvent true
        }
        if (isOk) {
          // tap = open, hold = app options (focused app only)
          when (key.action) {
            KeyEvent.ACTION_DOWN -> if (key.repeatCount == 0) { okDown = true; longPressed = false }
              else if (okDown && !longPressed && key.repeatCount >= 1) {
                longPressed = true
                focusedApp()?.let { menuApp = it }
              }
            KeyEvent.ACTION_UP -> { if (okDown && !longPressed) activate(); okDown = false }
          }
          return@onPreviewKeyEvent true
        }
        if (key.action != KeyEvent.ACTION_DOWN) return@onPreviewKeyEvent false
        navigate(key.keyCode)
      }
  ) {
    home?.let { h ->
      Rive(
        file = file,
        modifier = Modifier.fillMaxSize(),
        viewModelInstance = h,
        fit = Fit.Contain(),
        backgroundColor = theme.background.toArgb(),
      )
    }
  }

  when (settingsMenu) {
    SettingsMenu.NONE -> {}
    SettingsMenu.MAIN -> OptionsMenu(
      title = "Settings",
      options = listOf(
        "Android settings" to {
          settingsMenu = SettingsMenu.NONE
          launch(Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
        },
        "Screensaver settings" to {
          settingsMenu = SettingsMenu.NONE
          launch(Intent("com.google.android.tv.settings.ambient").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK))
        },
      ),
      onDismiss = { settingsMenu = SettingsMenu.NONE },
    )
    SettingsMenu.THEME -> OptionsMenu(
      title = "Theme",
      options = LauncherTheme.entries.map { t ->
        (if (t == theme) "${t.label}  ✓" else t.label) to { settingsMenu = SettingsMenu.NONE; if (t != theme) onPickTheme(t) }
      },
      onDismiss = { settingsMenu = SettingsMenu.NONE },
    )
  }

  menuApp?.let { app ->
    AppActionMenu(
      app = app,
      isFavorite = app.pkg in favs,
      onDismiss = { menuApp = null },
      onOpen = { menuApp = null; launch(app.intent) },
      onMove = { menuApp = null; orderBeforeMove = order; movingPkg = app.pkg },
      onToggleFavorite = {
        menuApp = null
        favs = if (app.pkg in favs) favs - app.pkg else favs + app.pkg
        prefs.edit().putStringSet("favs", favs).apply()
      },
      onAppInfo = {
        menuApp = null
        launch(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${app.pkg}")))
      },
    )
  }
}

private fun ImageBitmap.toPng(): ByteArray =
  ByteArrayOutputStream().use { out ->
    asAndroidBitmap().compress(Bitmap.CompressFormat.PNG, 100, out)
    out.toByteArray()
  }
