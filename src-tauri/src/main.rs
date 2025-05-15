#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::env;
use std::process::Command;
use std::path::PathBuf;
use tauri::{Builder, generate_context};

fn main() {
    Builder::default()
        .setup(|_app| {
            // Get the path to the Python directory
            let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
            let python_dir = manifest_dir
                .parent() // project root
                .unwrap()
                .join("src-py");

            // Print for debugging
            println!("Python directory: {}", python_dir.display());

            // Launch Python application
            let mut cmd = Command::new("python");
            cmd.current_dir(&python_dir)
               .arg("-c")
               .arg(r#"
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath('.')))
from tickr_backend.main import run_app
run_app()
               "#);

            #[cfg(target_os = "windows")]
            {
                use std::os::windows::process::CommandExt;
                cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW flag
            }

            cmd.spawn()
               .expect("Failed to start Python app");
            
            Ok(())
        })
        .run(generate_context!())
        .expect("error while running tauri application");
}