using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Media;
using System.Reflection;
using System.Security.Cryptography;
using System.Windows.Forms;
using Memory.Win64;
using static Testicles.ConsoleH;

namespace Testicles
{
    public partial class Form1 : Form
    {
        internal const string SupportedHash = "7dc947be34970da1e1c787bcddbe7f62b610ff258aebf8f06aa8b348f3a031d5";
        private const ulong GameStateRva = 0x332F260;
        private const ulong TooltipRva = 0x333CFB8;
        private MemoryHelper64 helper;
        private SoundPlayer soundPlayer;
        private Stream audioStream;
        private bool music = true;
        private bool console;
        private readonly List<Flag> flags = new List<Flag>();
        private sealed class Flag { public ulong Rva; public Label Status; }

        public Form1()
        {
            InitializeComponent();
            Text = "AdamHook - HOI4 1.19.3 (c01a)";
            label13.Text = "Start HOI4 and load a save first";
            label33.Text = "Build: 1.19.3.0.c01a";
            label14.AutoSize = true;
            timer1.Interval = 500;
            soundPlayer = new SoundPlayer();
            AddFlag(0x332F63A, label4, button3, button4);
            AddFlag(0x332F618, label5, button5, button2);
            AddFlag(0x332EC69, label6, button7, button6);
            AddFlag(0x332F616, label30, button23, button22);
            AddFlag(0x332F628, label18, button11, button10);
            AddFlag(0x332F617, label20, button13, button12);
            AddFlag(0x332F644, label22, button15, button14);
            AddFlag(0x332F62B, label24, button17, button16);
            AddFlag(0x332F62C, label26, button19, button18);
            AddFlag(0x332F631, label28, button21, button20);
            SetControls(false);
        }

        private void AddFlag(ulong rva, Label status, Button on, Button off)
        {
            flags.Add(new Flag { Rva = rva, Status = status });
            on.Click += (s, e) => WriteFlag(rva, 1);
            off.Click += (s, e) => WriteFlag(rva, 0);
        }
        private void SetControls(bool enabled)
        {
            foreach (Control control in Controls)
                if (control is Button && control != button24 && control != button25)
                    control.Enabled = enabled;
            textBox1.Enabled = enabled;
        }
        private void Form1_Load(object sender, EventArgs e)
        {
            try
            {
                var processes = Process.GetProcessesByName("hoi4");
                if (processes.Length != 1)
                    throw new InvalidOperationException("Start exactly one HOI4 instance, then restart AdamHook.");
                Process game = processes[0];
                string hash;
                using (var sha = SHA256.Create())
                using (var file = File.OpenRead(game.MainModule.FileName))
                    hash = BitConverter.ToString(sha.ComputeHash(file)).Replace("-", "").ToLowerInvariant();
                if (hash != SupportedHash)
                    throw new InvalidOperationException("Unsupported hoi4.exe. This build requires 1.19.3.0.c01a (exact Steam executable).");
                helper = new MemoryHelper64(game);
                SetControls(true);
                RefreshState();
                timer1.Start();
                LoadEmbeddedAudio("purgatory.wav");
            }
            catch (Exception ex) { Disconnect(ex); }
        }
        private ulong PointerField(ulong pointerRva, ulong offset)
        {
            ulong pointer = helper.ReadMemory<ulong>(helper.GetBaseAddress(pointerRva));
            return pointer < 0x10000 ? 0 : checked(pointer + offset);
        }
        private void RefreshState()
        {
            foreach (Flag flag in flags)
            {
                byte value = helper.ReadMemory<byte>(helper.GetBaseAddress(flag.Rva));
                if (value > 1) throw new InvalidOperationException("Unexpected flag value. No further writes allowed.");
                flag.Status.Text = value == 0 ? "Off" : "On";
            }
            ulong tooltip = PointerField(TooltipRva, 0x80);
            button8.Enabled = button9.Enabled = tooltip != 0;
            label12.Text = tooltip == 0 ? "N/A" : (helper.ReadMemory<byte>(tooltip) == 0 ? "Off" : "On");
            ulong country = PointerField(GameStateRva, 0x520);
            button1.Enabled = textBox1.Enabled = country != 0;
            label1.Text = country == 0 ? "Load save" : helper.ReadMemory<int>(country).ToString();
            label14.Text = "Connected: HOI4 1.19.3";
        }
        private void timer1_Tick_1(object sender, EventArgs e)
        {
            try { RefreshState(); }
            catch (Exception ex) { Disconnect(ex); }
        }
        private void WriteFlag(ulong rva, byte value)
        {
            Execute(() =>
            {
                ulong address = helper.GetBaseAddress(rva);
                if (helper.ReadMemory<byte>(address) > 1) throw new InvalidOperationException("Unexpected flag value.");
                helper.WriteMemory(address, value);
            });
        }
        private void Execute(Action action)
        {
            if (helper == null) return;
            try { action(); RefreshState(); }
            catch (Exception ex) { Disconnect(ex); }
        }
        private void Disconnect(Exception error)
        {
            timer1.Stop();
            SetControls(false);
            if (helper != null) helper.Dispose();
            helper = null;
            label14.Text = "Not connected";
            foreach (Flag flag in flags) flag.Status.Text = "N/A";
            label1.Text = label12.Text = "N/A";
            MessageBox.Show(this, error.Message, "AdamHook", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        private void button1_Click(object sender, EventArgs e)
        {
            int id;
            if (!int.TryParse(textBox1.Text, out id) || id <= 0)
            {
                MessageBox.Show(this, "Enter a positive numeric country ID from Tdebug.", "AdamHook");
                return;
            }
            Execute(() => helper.WriteMemory(PointerField(GameStateRva, 0x520), id));
        }
        private void button8_Click_1(object sender, EventArgs e)
        { Execute(() => helper.WriteMemory(PointerField(TooltipRva, 0x80), (byte)1)); }
        private void button9_Click(object sender, EventArgs e)
        { Execute(() => helper.WriteMemory(PointerField(TooltipRva, 0x80), (byte)0)); }
        private void LoadEmbeddedAudio(string name)
        {
            try
            {
                audioStream = Assembly.GetExecutingAssembly().GetManifestResourceStream("Testicles." + name);
                if (audioStream == null) return;
                soundPlayer.Stream = audioStream;
                soundPlayer.Load();
                if (music) soundPlayer.PlayLooping();
            }
            catch { music = false; }
        }
        private void button24_Click(object sender, EventArgs e)
        {
            music = !music;
            if (music && audioStream != null) soundPlayer.PlayLooping();
            else soundPlayer.Stop();
        }
        private void checkBox12_CheckedChanged(object sender, EventArgs e)
        {
            console = checkBox12.Checked;
            if (console)
            {
                ConsoleHelper.AllocConsole();
                Console.SetOut(new StreamWriter(Console.OpenStandardOutput()) { AutoFlush = true });
                Console.WriteLine("AdamHook: HOI4 1.19.3.0.c01a");
            }
            else { Console.SetOut(TextWriter.Null); ConsoleHelper.FreeConsole(); }
        }
        private void button25_Click(object sender, EventArgs e)
        { if (console) Console.WriteLine(label14.Text); }
        private void label23_Click(object sender, EventArgs e) { }
        private void label12_Click(object sender, EventArgs e) { }
        private void linkLabel1_LinkClicked(object sender, LinkLabelLinkClickedEventArgs e)
        { Process.Start("https://discord.com/invite/tZMQwYdJjq"); }
        private void linkLabel2_LinkClicked(object sender, LinkLabelLinkClickedEventArgs e)
        { Process.Start("https://www.youtube.com/channel/UCusIfQZ-BsQK0ktgV9bOAJw"); }
        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            timer1.Stop();
            if (helper != null) helper.Dispose();
            soundPlayer.Stop();
            soundPlayer.Dispose();
            if (audioStream != null) audioStream.Dispose();
            if (console) { Console.SetOut(TextWriter.Null); ConsoleHelper.FreeConsole(); }
            base.OnFormClosed(e);
        }
    }
}
