fn main() {
    println!("cargo:rerun-if-env-changed=STELLA_BUILD_PROFILE");
    if let Ok(profile) = std::env::var("STELLA_BUILD_PROFILE") {
        println!("cargo:rustc-env=STELLA_BUILD_PROFILE={profile}");
    }
    // 与桌面壳一致：静态链接 VC++ 运行库，干净 Windows 上安装器本身不能依赖 VCRUNTIME140*.dll。
    // tauri-build 2.7 起这也是默认值，这里显式写出，并清掉会覆盖属性的弃用环境变量。
    std::env::remove_var("STATIC_VCRUNTIME");
    let windows = tauri_build::WindowsAttributes::new().static_vc_runtime(true);
    tauri_build::try_build(tauri_build::Attributes::new().windows_attributes(windows))
        .expect("failed to run tauri-build");
}
