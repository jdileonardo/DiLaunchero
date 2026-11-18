package com.jdileonardo.dilaunchero

import android.content.ComponentName
import android.content.Intent
import android.net.Uri
import android.graphics.Bitmap
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.Bundle
import android.provider.Settings
import android.view.KeyEvent
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.Canvas
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.ui.graphics.Brush
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.input.key.onPreviewKeyEvent
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.core.graphics.drawable.toBitmap
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap

/** Packages never shown in the grid. Edit and rebuild. */
private val HIDDEN = setOf(
  "com.google.android.videos", // Play Movies
  "com.android.tv.settings",   // has its own button, top right
)
private const val SETTINGS_PKG = "com.android.tv.settings"

data class AppEntry(val pkg: String, val label: String, val intent: Intent)
data class NowPlaying(
  val app: String,
  val title: String?,
  val artist: String?,
  val playing: Boolean,
  val art: ImageBitmap?,
  val canPrevious: Boolean,
  val canToggle: Boolean,
  val canNext: Boolean,
)

/** true: the Rive UI (RiveHome.kt). false: the original Compose UI below. */
private const val USE_RIVE_UI = true

class MainActivity : ComponentActivity() {
  internal var refresh by mutableIntStateOf(0)
  private val icons = ConcurrentHashMap<String, ImageBitmap>()
  @Volatile internal var mediaController: MediaController? = null
  private var artKey: String? = null
  private var cachedArt: ImageBitmap? = null

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    if (USE_RIVE_UI) app.rive.runtime.kotlin.core.Rive.init(applicationContext) // loads the native runtime
    setContent { if (USE_RIVE_UI) RiveLauncherScreen() else LauncherScreen() }
  }

  override fun onResume() {
    super.onResume()
    refresh++ // pick up installs/uninstalls
  }

  internal fun launch(i: Intent) { runCatching { startActivity(i) } }

  internal fun icon(pkg: String): ImageBitmap = icons.getOrPut(pkg) {
    packageManager.getApplicationIcon(pkg).toBitmap(160, 160).asImageBitmap()
  }

  @Composable
  private fun LauncherScreen() {
    var apps by remember { mutableStateOf<List<AppEntry>>(emptyList()) }
    LaunchedEffect(refresh) { apps = withContext(Dispatchers.Default) { loadApps() } }

    var now by remember { mutableStateOf(Date()) }
    LaunchedEffect(Unit) { while (true) { now = Date(); delay(15_000) } }

    var playing by remember { mutableStateOf<NowPlaying?>(null) }
    LaunchedEffect(Unit) { while (true) { playing = withContext(Dispatchers.Default) { queryNowPlaying() }; delay(2_000) } }

    val focusRequesters = remember(apps) { apps.associate { it.pkg to FocusRequester() } }

    val prefs = remember { getSharedPreferences("launcher", MODE_PRIVATE) }
    var favs by remember { mutableStateOf(prefs.getStringSet("favs", emptySet()) ?: emptySet()) }
    fun toggleFav(pkg: String) {
      favs = if (pkg in favs) favs - pkg else favs + pkg
      prefs.edit().putStringSet("favs", favs).apply()
    }
    val focusedLabel = remember { mutableStateOf<String?>(null) }
    val focusedPkg = remember { mutableStateOf<String?>(null) }
    var menuApp by remember { mutableStateOf<AppEntry?>(null) }
    var order by remember { mutableStateOf(prefs.getString("app_order", "")!!.split('\n').filter { it.isNotEmpty() }) }
    var movingPkg by remember { mutableStateOf<String?>(null) }
    var focusAfterMove by remember { mutableStateOf<String?>(null) }
    var orderBeforeMove by remember { mutableStateOf<List<String>>(emptyList()) }
    val orderedApps = remember(apps, order) {
      val positions = order.withIndex().associate { it.value to it.index }
      apps.sortedWith(compareBy<AppEntry> { positions[it.pkg] ?: Int.MAX_VALUE }.thenBy { it.label.lowercase() })
    }
    val favApps = orderedApps.filter { it.pkg in favs }
    val otherApps = orderedApps.filter { it.pkg !in favs }
    val firstAppPkg = (favApps.firstOrNull() ?: otherApps.firstOrNull())?.pkg
    LaunchedEffect(firstAppPkg) { firstAppPkg?.let { runCatching { focusRequesters[it]?.requestFocus() } } }

    fun move(direction: Int) {
      val pkg = movingPkg ?: return
      val section = if (pkg in favs) favApps else otherApps
      val index = section.indexOfFirst { it.pkg == pkg }
      if (index < 0) return
      val target = (index + direction).coerceIn(0, section.lastIndex)
      if (target == index) return
      val changed = section.map { it.pkg }.toMutableList()
      changed.add(target, changed.removeAt(index))
      order = if (pkg in favs) changed + otherApps.map { it.pkg } else favApps.map { it.pkg } + changed
    }
    fun finishMove(save: Boolean) {
      val pkg = movingPkg
      if (save) prefs.edit().putString("app_order", order.joinToString("\n")).apply()
      else order = orderBeforeMove
      movingPkg = null
      focusAfterMove = pkg
    }
    BackHandler(enabled = true) {
      if (movingPkg != null) finishMove(false) // Back cancels a move.
      // Back on the home screen does nothing.
    }
    LaunchedEffect(movingPkg, order, focusAfterMove) {
      val pkg = movingPkg ?: focusAfterMove
      if (pkg != null) {
        // Reordered rows must attach before focus can return to the moved app.
        withFrameNanos { }
        runCatching { focusRequesters[pkg]?.requestFocus() }
        if (movingPkg == null) focusAfterMove = null
      }
    }

    Box(
      Modifier.fillMaxSize()
        .onPreviewKeyEvent { event ->
          val key = event.nativeKeyEvent
          if (key.action != KeyEvent.ACTION_DOWN) return@onPreviewKeyEvent false
          if (movingPkg != null) {
            when (key.keyCode) {
              KeyEvent.KEYCODE_DPAD_LEFT -> move(-1)
              KeyEvent.KEYCODE_DPAD_RIGHT -> move(1)
              KeyEvent.KEYCODE_DPAD_UP -> move(if (movingPkg in favs) -6 else -8)
              KeyEvent.KEYCODE_DPAD_DOWN -> move(if (movingPkg in favs) 6 else 8)
              KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_ENTER, KeyEvent.KEYCODE_BUTTON_A -> finishMove(true)
              KeyEvent.KEYCODE_BUTTON_B -> finishMove(false)
              else -> return@onPreviewKeyEvent false
            }
            return@onPreviewKeyEvent true
          }
          val pkg = focusedPkg.value ?: return@onPreviewKeyEvent false
          val inFavorites = pkg in favs
          val section = if (inFavorites) favApps else otherApps
          val index = section.indexOfFirst { it.pkg == pkg }
          if (index < 0) return@onPreviewKeyEvent false
          val columns = if (inFavorites) 6 else 8
          val target = when (key.keyCode) {
            KeyEvent.KEYCODE_DPAD_LEFT -> section.getOrNull(index - 1)
            KeyEvent.KEYCODE_DPAD_RIGHT -> section.getOrNull(index + 1)
            KeyEvent.KEYCODE_DPAD_UP -> section.getOrNull(index - columns)
              ?: if (!inFavorites) favApps.getOrNull(((index % 8) * 6 / 8).coerceAtMost(favApps.lastIndex)) else null
            KeyEvent.KEYCODE_DPAD_DOWN -> section.getOrNull(index + columns)
              ?: if (inFavorites) otherApps.getOrNull((index % 6) * 8 / 6) else null
            else -> return@onPreviewKeyEvent false
          }
          if (target == null && key.keyCode == KeyEvent.KEYCODE_DPAD_UP && (inFavorites || favApps.isEmpty())) return@onPreviewKeyEvent false
          target?.let { focusRequesters[it.pkg]?.requestFocus() }
          true
        }
        .background(Color(0xFF101622))
    ) {
      Column(Modifier.fillMaxSize().padding(horizontal = 56.dp, vertical = 32.dp)) {
        Row(Modifier.fillMaxWidth().height(72.dp), verticalAlignment = Alignment.CenterVertically) {
          Column {
            Text(SimpleDateFormat("h:mm a", Locale.getDefault()).format(now), color = Color.White, fontSize = 30.sp)
            Text(SimpleDateFormat("EEE, MMM d", Locale.getDefault()).format(now), color = Color(0xFF9AA4B2), fontSize = 15.sp)
          }
          Spacer(Modifier.weight(1f))
          playing?.let { np ->
            NowPlayingChip(
              np,
              onPrevious = { runCatching { mediaController?.transportControls?.skipToPrevious() } },
              onToggle = {
                runCatching {
                  if (np.playing) mediaController?.transportControls?.pause()
                  else mediaController?.transportControls?.play()
                }
                playing = np.copy(playing = !np.playing)
              },
              onNext = { runCatching { mediaController?.transportControls?.skipToNext() } },
              onControlFocus = { focusedPkg.value = null },
            )
            Spacer(Modifier.width(24.dp))
          }
          Focusable(shape = RoundedCornerShape(28.dp), onClick = { launch(Intent("com.google.android.tv.settings.ambient").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }, onFocused = { focusedPkg.value = null }) {
            ScreenSaverIcon(Modifier.size(40.dp))
          }
          Spacer(Modifier.width(12.dp))
          Focusable(shape = RoundedCornerShape(28.dp), onClick = { launch(Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }, onFocused = { focusedPkg.value = null }) {
            val si = remember { runCatching { icon(SETTINGS_PKG) }.getOrNull() }
            if (si != null) Image(si, "Settings", Modifier.size(40.dp)) else Text("Settings", color = Color.White)
          }
        }
        Spacer(Modifier.height(16.dp))
        // A small eager layout keeps remote focus movement responsive.
        Box(Modifier.weight(1f)) {
          Column(
            Modifier.fillMaxSize().verticalScroll(rememberScrollState())
              .padding(start = 8.dp, top = 16.dp, end = 8.dp, bottom = 96.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
          ) {
            if (favApps.isNotEmpty()) BoxWithConstraints(Modifier.fillMaxWidth()) {
              // Fixed tile width (same as a full row of 6) so a partial last row can be centered.
              val tileWidth = (maxWidth - 16.dp * 5) / 6
              Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                favApps.chunked(6).forEach { row ->
                  Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterHorizontally)) {
                    row.forEach { app ->
                      key(app.pkg) {
                        AppTile(app, Modifier.width(tileWidth), 84.dp, 14.dp, focusRequesters.getValue(app.pkg),
                          app.pkg == movingPkg, { focusedPkg.value = app.pkg; focusedLabel.value = it },
                          { menuApp = app }, { finishMove(true) })
                      }
                    }
                  }
                }
              }
            }
            if (favApps.isNotEmpty() && otherApps.isNotEmpty()) {
              Box(
                Modifier.fillMaxWidth().padding(vertical = 12.dp).height(2.dp).clip(RoundedCornerShape(1.dp))
                  .background(Brush.horizontalGradient(listOf(Color.Transparent, Color(0xFF3A4A66), Color.Transparent)))
              )
            }
            otherApps.chunked(8).forEach { row ->
              Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                row.forEach { app ->
                  key(app.pkg) {
                    AppTile(app, Modifier.weight(1f), 60.dp, 10.dp, focusRequesters.getValue(app.pkg),
                      app.pkg == movingPkg, { focusedPkg.value = app.pkg; focusedLabel.value = it },
                      { menuApp = app }, { finishMove(true) })
                  }
                }
                repeat(8 - row.size) { Spacer(Modifier.weight(1f)) }
              }
            }
          }
          Box(Modifier.align(Alignment.TopCenter).fillMaxWidth().height(28.dp)
            .background(Brush.verticalGradient(listOf(Color(0xFF101622), Color.Transparent))))
        }
      }
      FocusedAppBar(focusedLabel, movingPkg != null)
    }
    menuApp?.let { app ->
      AppActionMenu(
        app = app,
        isFavorite = app.pkg in favs,
        onDismiss = { menuApp = null },
        onOpen = { menuApp = null; launch(app.intent) },
        onMove = {
          menuApp = null
          orderBeforeMove = order
          movingPkg = app.pkg
        },
        onToggleFavorite = { menuApp = null; toggleFav(app.pkg) },
        onAppInfo = {
          menuApp = null
          launch(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${app.pkg}")))
        },
      )
    }
  }

  @Composable
  private fun BoxScope.FocusedAppBar(label: State<String?>, moving: Boolean) {
    Box(
      Modifier.align(Alignment.BottomCenter).fillMaxWidth().height(80.dp)
        .background(Brush.verticalGradient(listOf(Color.Transparent, Color(0xEE0B0E14)))),
      contentAlignment = Alignment.Center,
    ) {
      Text(label.value ?: "", color = Color.White, fontSize = 22.sp, maxLines = 1)
      Text(
        if (moving) "Arrows to move  •  OK to save  •  Back to cancel" else "Hold OK for app options",
        color = Color(0xFF6B778A), fontSize = 13.sp,
        modifier = Modifier.align(Alignment.CenterEnd).padding(end = 56.dp),
      )
    }
  }

  @Composable
  internal fun AppActionMenu(
    app: AppEntry,
    isFavorite: Boolean,
    onDismiss: () -> Unit,
    onOpen: () -> Unit,
    onMove: () -> Unit,
    onToggleFavorite: () -> Unit,
    onAppInfo: () -> Unit,
  ) {
    val firstOption = remember { FocusRequester() }
    // The long press can keep sending OK repeats after the dialog appears.
    var waitingForRelease by remember(app.pkg) { mutableStateOf(true) }
    Dialog(onDismissRequest = onDismiss) {
      Column(
        Modifier.width(360.dp)
          .onPreviewKeyEvent { event ->
            val key = event.nativeKeyEvent
            if (key.keyCode == KeyEvent.KEYCODE_BUTTON_B) {
              if (key.action == KeyEvent.ACTION_UP) onDismiss()
              return@onPreviewKeyEvent true
            }
            if (waitingForRelease && (key.keyCode == KeyEvent.KEYCODE_DPAD_CENTER || key.keyCode == KeyEvent.KEYCODE_ENTER || key.keyCode == KeyEvent.KEYCODE_BUTTON_A)) {
              when {
                key.action == KeyEvent.ACTION_UP -> {
                  waitingForRelease = false
                  return@onPreviewKeyEvent true
                }
                key.action == KeyEvent.ACTION_DOWN && key.repeatCount > 0 -> return@onPreviewKeyEvent true
                else -> waitingForRelease = false
              }
            }
            false
          }
          .clip(RoundedCornerShape(24.dp))
          .background(Color(0xFF1B2638))
          .padding(24.dp),
      ) {
        Text(app.label, color = Color.White, fontSize = 24.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Spacer(Modifier.height(16.dp))
        Focusable(Modifier.fillMaxWidth().focusRequester(firstOption), RoundedCornerShape(12.dp), onOpen) {
          Text("Open", color = Color.White, fontSize = 18.sp)
        }
        Spacer(Modifier.height(8.dp))
        Focusable(Modifier.fillMaxWidth(), RoundedCornerShape(12.dp), onToggleFavorite) {
          Text(if (isFavorite) "Remove from favorites" else "Add to favorites", color = Color.White, fontSize = 18.sp)
        }
        Spacer(Modifier.height(8.dp))
        Focusable(Modifier.fillMaxWidth(), RoundedCornerShape(12.dp), onMove) {
          Text("Move", color = Color.White, fontSize = 18.sp)
        }
        Spacer(Modifier.height(8.dp))
        Focusable(Modifier.fillMaxWidth(), RoundedCornerShape(12.dp), onAppInfo) {
          Text("App info", color = Color.White, fontSize = 18.sp)
        }
      }
      LaunchedEffect(app.pkg) { firstOption.requestFocus() }
    }
  }

  @Composable
  private fun AppTile(
    app: AppEntry, modifier: Modifier, iconSize: androidx.compose.ui.unit.Dp, pad: androidx.compose.ui.unit.Dp,
    focusRequester: FocusRequester, isMoving: Boolean,
    onFocus: (String) -> Unit, onShowMenu: () -> Unit, onFinishMove: () -> Unit,
  ) {
    val bmp by produceState<ImageBitmap?>(icons[app.pkg], app.pkg) {
      if (value == null) value = withContext(Dispatchers.IO) { runCatching { icon(app.pkg) }.getOrNull() }
    }
    Focusable(
      modifier.focusRequester(focusRequester),
      RoundedCornerShape(18.dp),
      onClick = { if (isMoving) onFinishMove() else launch(app.intent) },
      onLongClick = if (isMoving) null else onShowMenu,
      onFocused = { onFocus(app.label) },
      highlighted = isMoving,
      padding = pad,
    ) {
      Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
        Box(Modifier.size(iconSize)) { bmp?.let { Image(it, app.label, Modifier.fillMaxSize()) } }
      }
    }
  }

  /** Monitor with a sun/moon, drawn so we need no icon library. */
  @Composable
  private fun ScreenSaverIcon(modifier: Modifier) {
    Canvas(modifier) {
      val w = size.width; val h = size.height
      val stroke = Stroke(width = w * 0.07f)
      drawRoundRect(Color.White, topLeft = Offset(w * 0.06f, h * 0.14f), size = Size(w * 0.88f, h * 0.56f), cornerRadius = CornerRadius(w * 0.08f), style = stroke)
      drawCircle(Color(0xFFFFD66B), radius = w * 0.1f, center = Offset(w * 0.68f, h * 0.34f))
      drawLine(Color.White, Offset(w * 0.5f, h * 0.7f), Offset(w * 0.5f, h * 0.86f), strokeWidth = w * 0.07f)
      drawLine(Color.White, Offset(w * 0.3f, h * 0.88f), Offset(w * 0.7f, h * 0.88f), strokeWidth = w * 0.07f)
    }
  }

  @Composable
  private fun NowPlayingChip(
    np: NowPlaying,
    onPrevious: () -> Unit,
    onToggle: () -> Unit,
    onNext: () -> Unit,
    onControlFocus: () -> Unit,
  ) {
    Row(
      Modifier.clip(RoundedCornerShape(20.dp)).background(Color(0xFF1B2A3D)).padding(horizontal = 10.dp, vertical = 8.dp),
      verticalAlignment = Alignment.CenterVertically,
    ) {
      np.art?.let { Image(it, "Album art", Modifier.size(52.dp).clip(RoundedCornerShape(10.dp))) }
      if (np.art != null) Spacer(Modifier.width(12.dp))
      Column(Modifier.widthIn(max = 360.dp)) {
        Text(np.title ?: np.app, color = Color.White, fontSize = 17.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(listOfNotNull(np.artist, np.app).joinToString(" · "), color = Color(0xFF9AA4B2), fontSize = 13.sp,
          maxLines = 1, overflow = TextOverflow.Ellipsis)
      }
      if (np.canPrevious || np.canToggle || np.canNext) Spacer(Modifier.width(12.dp))
      if (np.canPrevious) {
        Focusable(modifier = Modifier.semantics { contentDescription = "Previous track" }, shape = RoundedCornerShape(10.dp), onClick = onPrevious, onFocused = onControlFocus, padding = 5.dp) {
          Text("⏮", color = Color.White, fontSize = 23.sp)
        }
      }
      if (np.canToggle) {
        Focusable(modifier = Modifier.semantics { contentDescription = if (np.playing) "Pause" else "Play" }, shape = RoundedCornerShape(10.dp), onClick = onToggle, onFocused = onControlFocus, padding = 5.dp) {
          Text(if (np.playing) "⏸" else "▶", color = Color.White, fontSize = 23.sp)
        }
      }
      if (np.canNext) {
        Focusable(modifier = Modifier.semantics { contentDescription = "Next track" }, shape = RoundedCornerShape(10.dp), onClick = onNext, onFocused = onControlFocus, padding = 5.dp) {
          Text("⏭", color = Color.White, fontSize = 23.sp)
        }
      }
    }
  }

  @OptIn(ExperimentalFoundationApi::class)
  @Composable
  private fun Focusable(
    modifier: Modifier = Modifier,
    shape: RoundedCornerShape,
    onClick: () -> Unit,
    onLongClick: (() -> Unit)? = null,
    onFocused: () -> Unit = {},
    highlighted: Boolean = false,
    padding: androidx.compose.ui.unit.Dp = 10.dp,
    content: @Composable () -> Unit,
  ) {
    val focused = remember { mutableStateOf(false) }
    var gamepadPressed by remember { mutableStateOf(false) }
    var gamepadLongClickTriggered by remember { mutableStateOf(false) }
    Box(
      modifier
        .onPreviewKeyEvent { event ->
          val key = event.nativeKeyEvent
          if (key.keyCode != KeyEvent.KEYCODE_BUTTON_A) return@onPreviewKeyEvent false
          when (key.action) {
            KeyEvent.ACTION_DOWN -> {
              if (key.repeatCount == 0) {
                gamepadPressed = true
                gamepadLongClickTriggered = false
              } else if (gamepadPressed && !gamepadLongClickTriggered && onLongClick != null) {
                gamepadLongClickTriggered = true
                onLongClick()
              }
            }
            KeyEvent.ACTION_UP -> {
              if (gamepadPressed && !gamepadLongClickTriggered) onClick()
              gamepadPressed = false
              gamepadLongClickTriggered = false
            }
          }
          true
        }
        .onFocusChanged { focused.value = it.isFocused; if (it.isFocused) onFocused() }
        .clip(shape)
        .background(Color(0xFF1B202B))
        .drawWithContent {
          val radius = CornerRadius(shape.topStart.toPx(size, this))
          if (focused.value) drawRoundRect(Color(0xFF2A3650), cornerRadius = radius)
          drawContent()
          if (focused.value || highlighted) {
            drawRoundRect(
              if (highlighted) Color(0xFFFFD66B) else Color(0xFFBFD4FF),
              cornerRadius = radius,
              style = Stroke(width = 2.dp.toPx()),
            )
          }
        }
        .combinedClickable(onClick = onClick, onLongClick = onLongClick)
        .padding(padding),
    ) { content() }
  }

  internal fun queryNowPlaying(): NowPlaying? = try {
    val msm = getSystemService(MediaSessionManager::class.java)
    val sessions: List<MediaController> = msm.getActiveSessions(ComponentName(this, NowPlayingListener::class.java))
    fun MediaController.isPlaying() = playbackState?.state == PlaybackState.STATE_PLAYING
    val c = sessions.firstOrNull { it.isPlaying() }
      ?: sessions.firstOrNull { it.playbackState?.state == PlaybackState.STATE_PAUSED }
    mediaController = c
    c?.let {
      val label = runCatching { packageManager.getApplicationLabel(packageManager.getApplicationInfo(it.packageName, 0)).toString() }.getOrDefault(it.packageName)
      val md = it.metadata
      val title = md?.getString(MediaMetadata.METADATA_KEY_TITLE)
      val artist = md?.getString(MediaMetadata.METADATA_KEY_ARTIST)
      val key = "${it.packageName}|$title|$artist"
      if (key != artKey) {
        val bitmap = md?.getBitmap(MediaMetadata.METADATA_KEY_ART)
          ?: md?.getBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART)
          ?: md?.getBitmap(MediaMetadata.METADATA_KEY_DISPLAY_ICON)
        cachedArt = bitmap?.let { source -> Bitmap.createScaledBitmap(source, 104, 104, true).asImageBitmap() }
        artKey = key
      }
      val actions = it.playbackState?.actions ?: 0L
      NowPlaying(label, title, artist, it.isPlaying(), cachedArt,
        actions and PlaybackState.ACTION_SKIP_TO_PREVIOUS != 0L,
        actions and (PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE or PlaybackState.ACTION_PLAY_PAUSE) != 0L,
        actions and PlaybackState.ACTION_SKIP_TO_NEXT != 0L)
    }
  } catch (e: SecurityException) { null } // notification-listener access not granted yet

  internal fun loadApps(): List<AppEntry> {
    val pm = packageManager
    fun query(cat: String) = pm.queryIntentActivities(Intent(Intent.ACTION_MAIN).addCategory(cat), 0)
    val leanback = query(Intent.CATEGORY_LEANBACK_LAUNCHER)
    val leanbackPkgs = leanback.map { it.activityInfo.packageName }.toSet()
    return (leanback + query(Intent.CATEGORY_LAUNCHER)).asSequence()
      .filter { it.activityInfo.packageName != packageName && it.activityInfo.packageName !in HIDDEN }
      .distinctBy { it.activityInfo.packageName }
      .map {
        val ai = it.activityInfo
        val cat = if (ai.packageName in leanbackPkgs) Intent.CATEGORY_LEANBACK_LAUNCHER else Intent.CATEGORY_LAUNCHER
        val intent = Intent(Intent.ACTION_MAIN).addCategory(cat).setClassName(ai.packageName, ai.name)
          .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED)
        AppEntry(ai.packageName, it.loadLabel(pm).toString(), intent)
      }
      .sortedBy { it.label.lowercase() }
      .toList()
  }
}
