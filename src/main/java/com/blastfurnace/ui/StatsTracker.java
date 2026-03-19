package com.blastfurnace.ui;

import com.blastfurnace.core.BarType;

/**
 * Tracks bot session statistics: bars smelted, XP gained, trips, profit, and rates.
 */
public class StatsTracker {

    private final long startTime;
    private int barsSmelted = 0;
    private int tripsMade = 0;
    private double xpGained = 0;
    private int coalUsed = 0;
    private int oreUsed = 0;
    private BarType barType;
    private boolean usingGoldsmithGauntlets = false;

    public StatsTracker(BarType barType, boolean usingGoldsmithGauntlets) {
        this.startTime = System.currentTimeMillis();
        this.barType = barType;
        this.usingGoldsmithGauntlets = usingGoldsmithGauntlets;
    }

    public void addBarsSmelted(int count) {
        barsSmelted += count;
        double xpPerBar = (barType == BarType.GOLD && usingGoldsmithGauntlets)
                ? barType.getGoldsmithXp() : barType.getXpPerBar();
        xpGained += count * xpPerBar;
    }

    public void addTrip() { tripsMade++; }
    public void addCoalUsed(int count) { coalUsed += count; }
    public void addOreUsed(int count) { oreUsed += count; }

    public int getBarsSmelted() { return barsSmelted; }
    public int getTripsMade() { return tripsMade; }
    public double getXpGained() { return xpGained; }
    public int getCoalUsed() { return coalUsed; }
    public int getOreUsed() { return oreUsed; }

    public long getElapsedMs() {
        return System.currentTimeMillis() - startTime;
    }

    public String getElapsedFormatted() {
        long elapsed = getElapsedMs();
        long seconds = (elapsed / 1000) % 60;
        long minutes = (elapsed / (1000 * 60)) % 60;
        long hours = elapsed / (1000 * 60 * 60);
        return String.format("%02d:%02d:%02d", hours, minutes, seconds);
    }

    public int getBarsPerHour() {
        long elapsed = getElapsedMs();
        if (elapsed == 0) return 0;
        return (int) (barsSmelted * 3600000.0 / elapsed);
    }

    public int getXpPerHour() {
        long elapsed = getElapsedMs();
        if (elapsed == 0) return 0;
        return (int) (xpGained * 3600000.0 / elapsed);
    }

    public int getTripsPerHour() {
        long elapsed = getElapsedMs();
        if (elapsed == 0) return 0;
        return (int) (tripsMade * 3600000.0 / elapsed);
    }

    public void setBarType(BarType barType) { this.barType = barType; }
    public BarType getBarType() { return barType; }
}
