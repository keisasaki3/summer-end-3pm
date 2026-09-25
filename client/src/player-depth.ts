import Phaser from "phaser";

const depthBias = new WeakMap<Phaser.GameObjects.Container, number>();
let nextBias = 0;

const sortPlayersByFeet = () => {
  const games = ((Phaser as any).GAMES ?? []) as Phaser.Game[];

  for (const game of games) {
    for (const scene of game.scene.getScenes(true)) {
      for (const child of scene.children.list) {
        if (!(child instanceof Phaser.GameObjects.Container)) continue;
        if (!child.getData("sprite")) continue;

        let bias = depthBias.get(child);
        if (bias === undefined) {
          bias = (nextBias++ % 1000) * 0.0001;
          depthBias.set(child, bias);
        }

        // Player coordinates are their feet. A larger Y means the character
        // stands closer to the camera, so it must be drawn in front.
        child.setDepth(10 + child.y + bias);
      }
    }
  }

  requestAnimationFrame(sortPlayersByFeet);
};

requestAnimationFrame(sortPlayersByFeet);
