package com.blastfurnace.utils;

import org.dreambot.api.input.Mouse;
import org.dreambot.api.methods.input.Camera;
import org.dreambot.api.methods.tabs.Tab;
import org.dreambot.api.methods.tabs.Tabs;

import java.util.concurrent.ThreadLocalRandom;

/**
 * Anti-pattern utilities to add human-like variability to bot actions.
 */
public final class AntiPattern {

    private static long lastAntiPatternTime = 0;
    private static final int ANTI_PATTERN_INTERVAL_MS = 45000;

    private AntiPattern() {}

    /**
     * Periodically perform a random human-like action.
     * Call this every loop iteration; it self-throttles.
     */
    public static void performIfDue() {
        long now = System.currentTimeMillis();
        if (now - lastAntiPatternTime < ANTI_PATTERN_INTERVAL_MS) return;

        int roll = ThreadLocalRandom.current().nextInt(100);

        if (roll < 20) {
            moveMouseRandomly();
        } else if (roll < 35) {
            rotateCameraSlightly();
        } else if (roll < 45) {
            checkRandomTab();
        } else if (roll < 55) {
            hoverInventoryItem();
        }
        // 55-100: do nothing (natural idle)

        lastAntiPatternTime = now;
    }

    private static void moveMouseRandomly() {
        int x = ThreadLocalRandom.current().nextInt(100, 700);
        int y = ThreadLocalRandom.current().nextInt(100, 450);
        Mouse.move(new java.awt.Point(x, y));
        SleepUtils.randomSleep(200, 600);
    }

    private static void rotateCameraSlightly() {
        int yawDelta = ThreadLocalRandom.current().nextInt(-60, 61);
        Camera.rotateTo(Camera.getYaw() + yawDelta, Camera.getPitch());
        SleepUtils.randomSleep(300, 800);
    }

    private static void checkRandomTab() {
        Tab[] tabs = { Tab.STATS, Tab.EQUIPMENT, Tab.QUEST };
        Tab randomTab = tabs[ThreadLocalRandom.current().nextInt(tabs.length)];
        Tabs.open(randomTab);
        SleepUtils.randomSleep(800, 2000);
        Tabs.open(Tab.INVENTORY);
        SleepUtils.randomSleep(200, 400);
    }

    private static void hoverInventoryItem() {
        Mouse.move(new java.awt.Point(
                ThreadLocalRandom.current().nextInt(560, 735),
                ThreadLocalRandom.current().nextInt(210, 460)
        ));
        SleepUtils.randomSleep(300, 700);
    }
}
