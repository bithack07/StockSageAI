// StockSage AI — Tauri v2 Desktop Entry Point
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod tray;

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_sql::Builder::default()
            .add_migrations("sqlite:stocksage.db", vec![
                tauri_plugin_sql::Migration {
                    version: 1,
                    description: "create_local_cache",
                    sql: include_str!("../migrations/001_init.sql"),
                    kind: tauri_plugin_sql::MigrationKind::Up,
                },
            ])
            .build()
        )
        .setup(|app| {
            tray::create_tray(app)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn main() {
    stocksage_lib::run();
}
