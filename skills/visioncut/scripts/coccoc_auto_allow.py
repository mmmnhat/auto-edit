"""
Auto-dismiss Cốc Cốc / Chromium 136+ 'Cho phép gỡ lỗi từ xa?' (Remote Debugging Permission) modal.
Can be imported or spawned as a background helper before connecting to ws://127.0.0.1:9222.
"""
import subprocess
import time

PS_SCRIPT = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$ end = (Get-Date).AddSeconds(15)
while ((Get-Date) -lt $end) {
    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $cond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty, "Cho phép"
    )
    $btn = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
    if ($null -ne $btn) {
        $inv = $btn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        if ($null -ne $inv) {
            $inv.Invoke()
            Write-Output "AUTO_ALLOWED"
            break
        }
    }
    Start-Sleep -Milliseconds 150
}
"""

def spawn_auto_allow():
    return subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", PS_SCRIPT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

if __name__ == "__main__":
    p = spawn_auto_allow()
    p.wait()
