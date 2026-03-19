package com.blastfurnace.ui;

import com.blastfurnace.core.BotState;

import java.awt.*;

/**
 * Renders the on-screen paint overlay showing bot statistics and current state.
 */
public class PaintOverlay {

    private static final Color BG_COLOR = new Color(0, 0, 0, 180);
    private static final Color TITLE_COLOR = new Color(255, 152, 0);
    private static final Color TEXT_COLOR = new Color(255, 255, 255);
    private static final Color ACCENT_COLOR = new Color(76, 175, 80);
    private static final Font TITLE_FONT = new Font("Arial", Font.BOLD, 14);
    private static final Font TEXT_FONT = new Font("Arial", Font.PLAIN, 12);

    private static final int X = 10;
    private static final int Y = 240;
    private static final int WIDTH = 220;
    private static final int LINE_HEIGHT = 18;
    private static final int PADDING = 8;

    private final StatsTracker stats;

    public PaintOverlay(StatsTracker stats) {
        this.stats = stats;
    }

    /**
     * Render the paint overlay onto the game screen.
     */
    public void render(Graphics2D g, BotState currentState) {
        String[] lines = buildLines(currentState);
        int height = PADDING * 2 + LINE_HEIGHT * (lines.length + 1);

        // Background
        g.setColor(BG_COLOR);
        g.fillRoundRect(X, Y, WIDTH, height, 10, 10);

        // Border
        g.setColor(TITLE_COLOR);
        g.drawRoundRect(X, Y, WIDTH, height, 10, 10);

        // Title
        g.setFont(TITLE_FONT);
        g.setColor(TITLE_COLOR);
        g.drawString("Blast Furnace Bot", X + PADDING, Y + PADDING + 14);

        // Separator line
        g.setColor(new Color(255, 255, 255, 60));
        g.drawLine(X + PADDING, Y + PADDING + 20, X + WIDTH - PADDING, Y + PADDING + 20);

        // Stats lines
        g.setFont(TEXT_FONT);
        int lineY = Y + PADDING + 36;
        for (String line : lines) {
            if (line.startsWith("*")) {
                // Accent color for state line
                g.setColor(ACCENT_COLOR);
                g.drawString(line.substring(1), X + PADDING, lineY);
            } else {
                g.setColor(TEXT_COLOR);
                g.drawString(line, X + PADDING, lineY);
            }
            lineY += LINE_HEIGHT;
        }
    }

    private String[] buildLines(BotState currentState) {
        return new String[] {
                "*State: " + currentState.getDescription(),
                "Bar: " + stats.getBarType().getBarName(),
                "Runtime: " + stats.getElapsedFormatted(),
                "Bars: " + formatNumber(stats.getBarsSmelted())
                        + " (" + formatNumber(stats.getBarsPerHour()) + "/hr)",
                "XP: " + formatNumber((int) stats.getXpGained())
                        + " (" + formatNumber(stats.getXpPerHour()) + "/hr)",
                "Trips: " + stats.getTripsMade()
                        + " (" + stats.getTripsPerHour() + "/hr)",
                "Ore used: " + formatNumber(stats.getOreUsed()),
                "Coal used: " + formatNumber(stats.getCoalUsed())
        };
    }

    private String formatNumber(int num) {
        if (num >= 1_000_000) return String.format("%.1fM", num / 1_000_000.0);
        if (num >= 1_000) return String.format("%.1fK", num / 1_000.0);
        return String.valueOf(num);
    }
}
