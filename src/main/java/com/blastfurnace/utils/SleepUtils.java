package com.blastfurnace.utils;

import org.dreambot.api.utilities.Sleep;

import java.util.concurrent.ThreadLocalRandom;

/**
 * Human-like sleep and delay utilities for anti-pattern behavior.
 */
public final class SleepUtils {

    private SleepUtils() {}

    /**
     * Sleep for a random duration between min and max milliseconds.
     */
    public static void randomSleep(int minMs, int maxMs) {
        Sleep.sleep(ThreadLocalRandom.current().nextInt(minMs, maxMs + 1));
    }

    /**
     * Short action delay simulating human reaction time.
     */
    public static void actionDelay() {
        randomSleep(150, 400);
    }

    /**
     * Slightly longer delay for between-state transitions.
     */
    public static void transitionDelay() {
        randomSleep(300, 700);
    }

    /**
     * Brief tick-aligned pause.
     */
    public static void tickSleep() {
        randomSleep(580, 650);
    }

    /**
     * Occasionally perform a longer idle to simulate AFK behavior.
     * Returns true if an idle was performed.
     */
    public static boolean maybeIdle(int chancePercent) {
        if (ThreadLocalRandom.current().nextInt(100) < chancePercent) {
            randomSleep(1200, 3500);
            return true;
        }
        return false;
    }

    /**
     * Random gaussian-distributed sleep centered around the mean.
     */
    public static void gaussianSleep(int meanMs, int stdDevMs) {
        double value = ThreadLocalRandom.current().nextGaussian() * stdDevMs + meanMs;
        int sleepTime = Math.max(50, (int) value);
        Sleep.sleep(sleepTime);
    }
}
