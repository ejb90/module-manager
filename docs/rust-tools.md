# Rust Tools

Rust CLIs can be copied directly into the versioned prefix.

```sh
module-manager deploy-rust ripgrep 14.1.1 \
  --binary ./target/release/rg \
  --prefix /prod/tools \
  --module-root /prod/modulefiles
```

This writes the binary to:

```text
/prod/tools/ripgrep/14.1.1/bin/ripgrep
```

and creates:

```text
/prod/modulefiles/ripgrep/14.1.1
```

The generated modulefile prepends the deployed `bin` directory to `PATH`.
