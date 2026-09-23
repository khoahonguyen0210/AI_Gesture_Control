# PlatformIO extra script: builds the shared protocol and device code from firmware/src.
Import("env")  # noqa: F821

env.BuildSources("$BUILD_DIR/shared", "$PROJECT_DIR/../src", "+<*.c>")  # noqa: F821
