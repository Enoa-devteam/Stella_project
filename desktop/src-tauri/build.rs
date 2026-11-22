fn main() {
    println!("cargo:rerun-if-env-changed=STELLA_BUILD_PROFILE");
    if let Ok(profile) = std::env::var("STELLA_BUILD_PROFILE") {
        println!("cargo:rustc-env=STELLA_BUILD_PROFILE={profile}");
    }
    // 静态链接 VC++ 运行库：干净 Windows 没有 VCRUNTIME140_1.dll，动态链接时壳根本起不来
    // （2026-11-22 Windows Sandbox 实测；v6.2.0–v6.4.0 均受影响）。锁定的 tauri-build 2.6
    // 只认这个环境变量，而 tauri-cli 2.12 不再设置它。CI 有 check_windows_crt.py 门禁兜底。
    std::env::set_var("STATIC_VCRUNTIME", "true");
    tauri_build::build()
}
