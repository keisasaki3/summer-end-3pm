import Phaser from "phaser";

// Keep the game's looping map audio alive when the browser tab/window loses focus.
// Phaser pauses audio on blur by default, and Web Audio is more likely to be
// suspended by browsers in the background, so use HTML5 Audio for map ambience.
const phaserRuntime = Phaser as any;
const OriginalGame = phaserRuntime.Game;

phaserRuntime.Game = class BackgroundAudioGame extends OriginalGame {
  constructor(config: any) {
    super({
      ...config,
      audio: {
        ...(config.audio ?? {}),
        disableWebAudio: true,
      },
    });
  }

  boot() {
    const result = super.boot();
    if (this.sound) {
      this.sound.pauseOnBlur = false;
    }
    return result;
  }
};

void import("./main");
