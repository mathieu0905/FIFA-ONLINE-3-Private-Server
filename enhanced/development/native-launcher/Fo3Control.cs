using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

class Fo3Control : Form {
    readonly string root = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".."));
    TextBox output = new TextBox();
    Button server = new Button(), stop = new Button(), client = new Button();
    bool busy;
    Fo3Control(bool serverMode) {
        Text = serverMode ? "FO3 服务端" : "FIFA Online 3";
        ClientSize = new Size(660, 390); StartPosition = FormStartPosition.CenterScreen;
        Font = new Font("Microsoft YaHei UI", 10); MinimumSize = Size; MaximizeBox = false;
        var label = new Label { Text = "服务端与客户端独立运行。先启动服务端，再打开游戏。", AutoSize=true, Left=18, Top=18 };
        Controls.Add(label);
        server.Text="启动服务端"; stop.Text="停止服务端"; client.Text="打开客户端";
        Button[] buttons = {server,stop,client};
        for(int i=0;i<buttons.Length;i++) { buttons[i].SetBounds(18+i*207,52,195,40); Controls.Add(buttons[i]); }
        server.Click += async (s,e) => await Action("server-start");
        stop.Click += async (s,e) => await Action("server-stop");
        client.Click += async (s,e) => await Action("client-start");
        output.SetBounds(18,108,624,262); output.Multiline=true; output.ReadOnly=true; output.ScrollBars=ScrollBars.Vertical;
        output.BackColor=Color.White; Controls.Add(output);
        Append("请选择操作。关闭本窗口不会停止已经运行的服务或游戏。");
        AcceptButton=serverMode?server:client;
        FormClosing += (s,e) => { if(busy) { e.Cancel=true; Append("当前步骤尚未完成，请稍候。"); } };
    }
    void Append(string line) {
        if(IsDisposed) return;
        if(InvokeRequired) { BeginInvoke(new Action<string>(Append),line);return; }
        output.AppendText(line+Environment.NewLine);
    }
    ProcessStartInfo Info(string action) {
        var p = new ProcessStartInfo(Path.Combine(root,@".venv\Scripts\python.exe"), "-B -u \""+Path.Combine(root,@"launcher\fo3_control.py")+"\" "+action);
        p.WorkingDirectory=root;p.UseShellExecute=false;p.CreateNoWindow=true;
        p.RedirectStandardOutput=true;p.RedirectStandardError=true;
        p.StandardOutputEncoding=Encoding.UTF8;p.StandardErrorEncoding=Encoding.UTF8;
        p.EnvironmentVariables["PYTHONIOENCODING"]="utf-8";return p;
    }
    async Task Action(string action) {
        busy=true;server.Enabled=stop.Enabled=client.Enabled=false;
        try {
            int code=await Task.Run(() => {
                using(var p=new Process { StartInfo=Info(action) }) {
                    p.OutputDataReceived += (s,e) => { if(e.Data!=null) Append(e.Data); };
                    p.ErrorDataReceived += (s,e) => { if(e.Data!=null) Append(e.Data); };
                    p.Start();p.BeginOutputReadLine();p.BeginErrorReadLine();p.WaitForExit();return p.ExitCode;
                }
            });
            if(code!=0) MessageBox.Show(this,"操作未完成，请查看窗口中的错误信息。","FO3",MessageBoxButtons.OK,MessageBoxIcon.Warning);
        } catch(Exception e) { Append("错误："+e.Message); }
        finally { busy=false;server.Enabled=stop.Enabled=client.Enabled=true; }
    }
    [STAThread] static int Main(string[] args) {
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
        var form=new Fo3Control(Array.IndexOf(args,"--server")>=0);
        if(Array.IndexOf(args,"--check-only")>=0) {
            var info=form.Info("check");
            using(var p=Process.Start(info)) {
                var stdout=p.StandardOutput.ReadToEndAsync();var stderr=p.StandardError.ReadToEndAsync();
                p.WaitForExit();Task.WaitAll(stdout,stderr);
                File.WriteAllText(Path.Combine(form.root,@"captures\native-launcher-check.log"),stdout.Result+stderr.Result,Encoding.UTF8);
                return p.ExitCode;
            }
        }
        Application.Run(form);return 0;
    }
}
