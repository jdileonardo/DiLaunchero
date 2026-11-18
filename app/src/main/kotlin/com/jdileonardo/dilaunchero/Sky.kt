package com.jdileonardo.dilaunchero

import android.content.Context
import java.util.Calendar
import java.util.TimeZone
import kotlin.math.acos
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.tan

/**
 * Day, dusk or night, for the themes that change with the sky (the skyPhase view model number).
 *
 * No location permission: sunrise and sunset come from the time zone's main city (or, for zones
 * not listed, the zone's meridian), unless "lat"/"lon" are set in the launcher's prefs.
 */
internal object Sky {
  const val NIGHT = 0
  const val DUSK = 1
  const val DAY = 2

  /** Minutes either side of sunrise and sunset that count as dusk (or dawn). */
  private const val TWILIGHT_MIN = 35

  /** Where we are: "lat"/"lon" from prefs if set, else a guess from the time zone. */
  fun place(context: Context): Pair<Double, Double> {
    val prefs = context.getSharedPreferences("launcher", Context.MODE_PRIVATE)
    if (prefs.contains("lat")) return prefs.getFloat("lat", 0f).toDouble() to prefs.getFloat("lon", 0f).toDouble()
    return guessFromTimeZone(TimeZone.getDefault())
  }

  /** A few common zones by their main city; anywhere else, the zone's own meridian at 40°N/S. */
  private fun guessFromTimeZone(tz: TimeZone): Pair<Double, Double> {
    val known = mapOf(
      "America/New_York" to (40.71 to -74.01), "America/Toronto" to (43.65 to -79.38),
      "America/Chicago" to (41.88 to -87.63), "America/Denver" to (39.74 to -104.99),
      "America/Los_Angeles" to (34.05 to -118.24), "America/Vancouver" to (49.28 to -123.12),
      "America/Halifax" to (44.65 to -63.57), "Europe/London" to (51.51 to -0.13),
      "Europe/Paris" to (48.86 to 2.35), "Europe/Rome" to (41.9 to 12.5),
      "Australia/Sydney" to (-33.87 to 151.21),
    )
    known[tz.id]?.let { return it }
    val lon = tz.rawOffset / 3_600_000.0 * 15
    return (if (tz.id.startsWith("Australia") || tz.id.startsWith("Pacific/Auckland")) -40.0 else 40.0) to lon
  }

  /** Night, dusk or day for this moment and place. */
  fun phase(now: Calendar, lat: Double, lon: Double): Int {
    val (rise, set) = sunTimes(now, lat, lon) ?: return if (polarDay(now, lat)) DAY else NIGHT
    val m = now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE)
    return when {
      m < rise - TWILIGHT_MIN || m > set + TWILIGHT_MIN -> NIGHT
      m < rise + TWILIGHT_MIN || m > set - TWILIGHT_MIN -> DUSK
      else -> DAY
    }
  }

  /** Summer at the poles: north in April to September, south otherwise. */
  private fun polarDay(now: Calendar, lat: Double) = (now.get(Calendar.MONTH) in Calendar.APRIL..Calendar.SEPTEMBER) == (lat > 0)

  /**
   * Sunrise and sunset in local minutes after midnight (NOAA's simplified equations, good to a few
   * minutes), or null during polar day or night.
   */
  fun sunTimes(now: Calendar, lat: Double, lon: Double): Pair<Double, Double>? {
    val day = now.get(Calendar.DAY_OF_YEAR)
    val g = 2 * Math.PI / 365 * (day - 1)
    val eqTime = 229.18 * (0.000075 + 0.001868 * cos(g) - 0.032077 * sin(g) - 0.014615 * cos(2 * g) - 0.040849 * sin(2 * g))
    val decl = 0.006918 - 0.399912 * cos(g) + 0.070257 * sin(g) - 0.006758 * cos(2 * g) +
      0.000907 * sin(2 * g) - 0.002697 * cos(3 * g) + 0.00148 * sin(3 * g)
    val latR = Math.toRadians(lat)
    val cosHa = cos(Math.toRadians(90.833)) / (cos(latR) * cos(decl)) - tan(latR) * tan(decl)
    if (cosHa < -1 || cosHa > 1) return null
    val ha = Math.toDegrees(acos(cosHa))
    val offsetMin = (now.get(Calendar.ZONE_OFFSET) + now.get(Calendar.DST_OFFSET)) / 60_000.0
    val noon = 720 - 4 * lon - eqTime + offsetMin
    return (noon - 4 * ha) to (noon + 4 * ha)
  }
}
