use std::io::{self, Read};

fn main() {
    let result = (|| {
        let mut input = String::new();
        io::stdin().take(8 * 1024 * 1024 + 1).read_to_string(&mut input).map_err(|e| e.to_string())?;
        if input.len() > 8 * 1024 * 1024 { return Err("request-too-large".into()); }
        let request = serde_json::from_str(&input).map_err(|e| format!("invalid-json: {e}"))?;
        anicanto_core::dispatch(request)
    })();
    match result {
        Ok(value) => println!("{}", serde_json::json!({"ok":true,"result":value})),
        Err(error) => {
            println!("{}", serde_json::json!({"ok":false,"error":error}));
            std::process::exit(2);
        }
    }
}
