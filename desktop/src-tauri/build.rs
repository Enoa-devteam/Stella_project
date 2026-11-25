fn main() {
    println!("cargo:rerun-if-env-changed=STELLA_BUILD_PROFILE");
    if let Ok(profile) = std::env::var("STELLA_BUILD_PROFILE") {
        println!("cargo:rustc-env=STELLA_BUILD_PROFILE={profile}");
    }
    // 静态链接 VC++ 运行库：干净 Windows 没有 VCRUNTIME140_1.dll，动态链接时壳根本起不来
    // （2026-11-22 Windows Sandbox 实测；v6.2.0–v6.4.0 均受影响）。tauri-build 2.7 起改用
    // WindowsAttributes::static_vc_runtime；旧的 STATIC_VCRUNTIME 环境变量已弃用但仍优先于
    // 属性，所以先清掉，避免外部环境里的 STATIC_VCRUNTIME=false 悄悄改回动态链接。
    // CI 有 check_windows_crt.py 门禁兜底。
    std::env::remove_var("STATIC_VCRUNTIME");
    let windows = tauri_build::WindowsAttributes::new().static_vc_runtime(true);
    tauri_build::try_build(tauri_build::Attributes::new().windows_attributes(windows))
        .expect("failed to run tauri-build");
}
