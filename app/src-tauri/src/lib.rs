mod commands;
mod db;

use db::Db;
use std::sync::Mutex;
use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        // Must be the first plugin registered, same reasoning as
        // WayStation's own lib.rs: a second Baneward process opening the
        // same SQLite file concurrently is a real resource-contention
        // risk, not a cosmetic one. A second launch (e.g. a future
        // baneward:// link from Citadel while Baneward's already open)
        // should focus the existing window, not spawn a competing one.
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_focus();
                let _ = window.unminimize();
            }
        }))
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // Dynamic runtime registration of the baneward:// scheme --
            // same real reason as WayStation's: only needed on Linux
            // dev/unbundled builds, since a packaged .deb/AppImage gets
            // its scheme association baked in by Tauri's bundler at
            // package time (driven by tauri.conf.json's own
            // plugins.deep-link config), and macOS/Windows installers
            // register it at install time too.
            #[cfg(target_os = "linux")]
            {
                use tauri_plugin_deep_link::DeepLinkExt;
                app.deep_link().register("baneward")?;
            }

            let conn = db::open(app.handle());
            app.manage(Db(Mutex::new(conn)));
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::search_species,
            commands::get_species,
            commands::add_claim,
            commands::verify_claim,
            commands::delete_claim,
            commands::add_user_image,
            commands::verify_user_image,
            commands::delete_user_image,
            commands::read_image_bytes,
            commands::image_pack_status,
            commands::download_image_pack,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
