package com.blastfurnace.ui;

import com.blastfurnace.core.BarType;
import com.blastfurnace.core.BotConfig;

import javax.swing.*;
import java.awt.*;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Configuration GUI displayed before the bot starts.
 * Allows the user to select bar type and toggle options.
 */
public class ConfigGUI {

    private final BotConfig config;
    private final AtomicBoolean started = new AtomicBoolean(false);
    private final AtomicBoolean cancelled = new AtomicBoolean(false);
    private JFrame frame;

    public ConfigGUI(BotConfig config) {
        this.config = config;
    }

    /**
     * Display the configuration GUI and block until the user clicks Start or Cancel.
     * Returns true if the user clicked Start, false if cancelled.
     */
    public boolean show() {
        SwingUtilities.invokeLater(this::buildGUI);

        // Block until user makes a choice
        while (!started.get() && !cancelled.get()) {
            try { Thread.sleep(100); } catch (InterruptedException ignored) {}
        }
        return started.get();
    }

    private void buildGUI() {
        frame = new JFrame("Blast Furnace Bot - Configuration");
        frame.setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
        frame.setSize(380, 420);
        frame.setLocationRelativeTo(null);
        frame.setResizable(false);

        JPanel mainPanel = new JPanel();
        mainPanel.setLayout(new BoxLayout(mainPanel, BoxLayout.Y_AXIS));
        mainPanel.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
        mainPanel.setBackground(new Color(45, 45, 48));

        // Title
        JLabel title = new JLabel("Blast Furnace Bot");
        title.setFont(new Font("Arial", Font.BOLD, 18));
        title.setForeground(new Color(255, 152, 0));
        title.setAlignmentX(Component.CENTER_ALIGNMENT);
        mainPanel.add(title);
        mainPanel.add(Box.createVerticalStrut(15));

        // Bar selection
        JPanel barPanel = createOptionPanel("Select Bar Type:");
        JComboBox<BarType> barCombo = new JComboBox<>(BarType.values());
        barCombo.setSelectedItem(BarType.GOLD);
        barCombo.setMaximumSize(new Dimension(250, 30));
        barPanel.add(barCombo);
        mainPanel.add(barPanel);
        mainPanel.add(Box.createVerticalStrut(10));

        // Options
        JPanel optionsPanel = createOptionPanel("Options:");

        JCheckBox coalBagCb = createCheckbox("Use Coal Bag (locked slot)", true);
        JCheckBox staminaCb = createCheckbox("Use Stamina Potions", true);
        JCheckBox iceGlovesCb = createCheckbox("Use Ice Gloves", true);
        JCheckBox goldsmithCb = createCheckbox("Use Goldsmith Gauntlets (Gold)", true);

        optionsPanel.add(coalBagCb);
        optionsPanel.add(staminaCb);
        optionsPanel.add(iceGlovesCb);
        optionsPanel.add(goldsmithCb);
        mainPanel.add(optionsPanel);
        mainPanel.add(Box.createVerticalStrut(10));

        // Coal bag slot
        JPanel slotPanel = createOptionPanel("Coal Bag Inventory Slot (0-27):");
        JSpinner slotSpinner = new JSpinner(new SpinnerNumberModel(0, 0, 27, 1));
        slotSpinner.setMaximumSize(new Dimension(80, 30));
        slotPanel.add(slotSpinner);
        mainPanel.add(slotPanel);
        mainPanel.add(Box.createVerticalStrut(15));

        // Info label
        JLabel infoLabel = new JLabel("<html><i>Gold must be deposited in coffer before starting.</i></html>");
        infoLabel.setForeground(new Color(200, 200, 200));
        infoLabel.setFont(new Font("Arial", Font.ITALIC, 11));
        infoLabel.setAlignmentX(Component.CENTER_ALIGNMENT);
        mainPanel.add(infoLabel);
        mainPanel.add(Box.createVerticalStrut(10));

        // Buttons
        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.CENTER, 15, 0));
        buttonPanel.setOpaque(false);

        JButton startBtn = new JButton("Start");
        startBtn.setBackground(new Color(76, 175, 80));
        startBtn.setForeground(Color.WHITE);
        startBtn.setFont(new Font("Arial", Font.BOLD, 14));
        startBtn.setPreferredSize(new Dimension(100, 35));
        startBtn.setFocusPainted(false);

        JButton cancelBtn = new JButton("Cancel");
        cancelBtn.setBackground(new Color(244, 67, 54));
        cancelBtn.setForeground(Color.WHITE);
        cancelBtn.setFont(new Font("Arial", Font.BOLD, 14));
        cancelBtn.setPreferredSize(new Dimension(100, 35));
        cancelBtn.setFocusPainted(false);

        startBtn.addActionListener(e -> {
            config.setSelectedBar((BarType) barCombo.getSelectedItem());
            config.setUseCoalBag(coalBagCb.isSelected());
            config.setUseStaminaPotions(staminaCb.isSelected());
            config.setUseIceGloves(iceGlovesCb.isSelected());
            config.setUseGoldsmithGauntlets(goldsmithCb.isSelected());
            config.setCoalBagSlot((int) slotSpinner.getValue());
            started.set(true);
            frame.dispose();
        });

        cancelBtn.addActionListener(e -> {
            cancelled.set(true);
            frame.dispose();
        });

        frame.addWindowListener(new java.awt.event.WindowAdapter() {
            @Override
            public void windowClosing(java.awt.event.WindowEvent e) {
                cancelled.set(true);
            }
        });

        buttonPanel.add(startBtn);
        buttonPanel.add(cancelBtn);
        mainPanel.add(buttonPanel);

        frame.setContentPane(mainPanel);
        frame.setVisible(true);
    }

    private JPanel createOptionPanel(String label) {
        JPanel panel = new JPanel();
        panel.setLayout(new BoxLayout(panel, BoxLayout.Y_AXIS));
        panel.setOpaque(false);
        panel.setAlignmentX(Component.LEFT_ALIGNMENT);

        JLabel lbl = new JLabel(label);
        lbl.setForeground(Color.WHITE);
        lbl.setFont(new Font("Arial", Font.BOLD, 12));
        panel.add(lbl);
        panel.add(Box.createVerticalStrut(5));
        return panel;
    }

    private JCheckBox createCheckbox(String text, boolean selected) {
        JCheckBox cb = new JCheckBox(text, selected);
        cb.setForeground(new Color(220, 220, 220));
        cb.setOpaque(false);
        cb.setFont(new Font("Arial", Font.PLAIN, 12));
        cb.setFocusPainted(false);
        return cb;
    }
}
