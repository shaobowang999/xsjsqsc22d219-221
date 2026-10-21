using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

internal static class Uninstall
{
    const string AppExe = "三千思创无线画布.exe";
    const string Manifest = "uninstall-files.txt";

    static string[] Validate(string root)
    {
        if (!File.Exists(Path.Combine(root, AppExe)) ||
            !Directory.Exists(Path.Combine(root, "_internal")))
            throw new Exception("请将 uninstall.exe 放在画布 EXE 旁边运行。");
        string prefix = root.TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        string[] files = File.ReadAllLines(Path.Combine(root, Manifest), Encoding.UTF8);
        if (files.Length == 0) throw new Exception("卸载清单为空。");
        foreach (string entry in files)
        {
            string rel = entry.Replace('/', '\\');
            if (!(rel == AppExe || rel == "uninstall.exe" || rel == Manifest ||
                  rel == "卸载说明.txt" || rel.StartsWith("_internal\\", StringComparison.Ordinal)) ||
                rel.Split('\\').Any(p => p == ".." || p == "." || p.Length == 0) ||
                rel.Contains(':') || Path.IsPathRooted(rel))
                throw new Exception("卸载清单包含不允许的路径：" + entry);
            string path = Path.GetFullPath(Path.Combine(root, rel));
            if (!path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                throw new Exception("卸载路径超出程序目录。");
            for (string current = path; current != null; current = Path.GetDirectoryName(current))
            {
                if ((File.Exists(current) || Directory.Exists(current)) &&
                    (File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
                    throw new Exception("检测到链接目录，请将程序解压到普通目录后再卸载。");
            }
        }
        return files;
    }

    [STAThread]
    static int Main(string[] args)
    {
        try
        {
            string self = Assembly.GetExecutingAssembly().Location;
            bool worker = args.Length == 2 && args[0] == "--remove";
            string root = Path.GetFullPath(worker ? args[1] : Path.GetDirectoryName(self)).TrimEnd('\\');
            string[] files = Validate(root);
            // Verification is read-only, for packaging checks.
            if (args.Length == 1 && args[0] == "--verify") return 0;
            if (!worker)
            {
                string helper = Path.Combine(Path.GetTempPath(), "sqsc-uninstall-" + Guid.NewGuid() + ".exe");
                File.Copy(self, helper);
                Process.Start(new ProcessStartInfo(helper, "--remove \"" + root + "\"")
                { UseShellExecute = false, WorkingDirectory = Path.GetTempPath() });
                return 0;
            }
            if (MessageBox.Show("确定卸载三千思创无线画布？\n\n目录：" + root +
                "\n\n请先关闭画布程序。仅删除发行清单中的程序文件，保留用户数据、API 密钥和其他文件。",
                "确认卸载", MessageBoxButtons.YesNo, MessageBoxIcon.Warning,
                MessageBoxDefaultButton.Button2) != DialogResult.Yes) return 0;

            files = Validate(root);
            // Refuse to start removal if any payload file is locked by a running app.
            foreach (string rel in files.Where(p => p != "uninstall.exe"))
            {
                string path = Path.Combine(root, rel);
                if (File.Exists(path)) using (File.Open(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None)) { }
            }
            int failed = 0;
            foreach (string rel in files.Where(p => p != Manifest && p != "uninstall.exe" && p != AppExe))
            {
                try { File.Delete(Path.Combine(root, rel)); }
                catch { failed++; }
            }
            if (failed != 0)
                throw new Exception("部分文件仍被占用或无权限，请关闭画布后再次运行卸载。已保留卸载程序与清单。");
            // Only remove empty directories derived from the file list; never recurse over user files.
            var dirs = files.Select(p => Path.GetDirectoryName(Path.Combine(root, p)))
                .Where(p => p != root).Distinct().OrderByDescending(p => p.Length);
            foreach (string dir in dirs)
            {
                string current = dir;
                while (current != root && Directory.Exists(current))
                {
                    try { Directory.Delete(current, false); }
                    catch (IOException) { break; }
                    current = Path.GetDirectoryName(current);
                }
            }
            File.Delete(Path.Combine(root, AppExe));
            File.Delete(Path.Combine(root, "uninstall.exe"));
            File.Delete(Path.Combine(root, Manifest));
            try { Directory.Delete(root, false); } catch (IOException) { }
            MessageBox.Show("程序已卸载。原有画布、API 配置及其他个人文件已保留。",
                "卸载完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return 0;
        }
        catch (Exception ex)
        {
            MessageBox.Show("无法完成卸载：\n" + ex.Message,
                "卸载提示", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
