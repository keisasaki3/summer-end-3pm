import Phaser from "phaser";

const PLAYER_DEPTH_BASE = 10;
const PLAYER_DEPTH_STEP = 0.01;
const Y_TIE_EPSILON = 0.01;

const isPlayerContainer = (child: any): child is Phaser.GameObjects.Container =>
  !!child && typeof child.getData === "function" && !!child.getData("sprite");

const sortPlayersByFeet = () => {
  const games = ((Phaser as any).GAMES ?? []) as Phaser.Game[];

  for (const game of games) {
    for (const scene of game.scene.getScenes(true)) {
      const players = scene.children.list.filter(isPlayerContainer);
      if (players.length < 1) continue;

      // TypeScript `private` is a normal runtime property here. When two
      // characters occupy the exact same feet coordinate, prefer the local
      // player as the final tie-breaker so it does not disappear underneath a
      // remote player. Outside an exact Y tie, ordinary 2D feet-Y sorting wins.
      const localPlayer = (scene as any).me as Phaser.GameObjects.Container | undefined;

      players.sort((a, b) => {
        const dy = a.y - b.y;
        if (Math.abs(dy) > Y_TIE_EPSILON) return dy;

        if (a === localPlayer && b !== localPlayer) return 1;
        if (b === localPlayer && a !== localPlayer) return -1;

        const dx = a.x - b.x;
        if (Math.abs(dx) > 0.01) return dx;

        // Stable deterministic fallback for remote-vs-remote exact overlap.
        return String(a.getData("playerName") ?? "").localeCompare(
          String(b.getData("playerName") ?? "")
        );
      });

      // Assign depth from the sorted order itself instead of adding a permanent
      // creation-order bias. This makes "lower feet = in front" symmetric for
      // the local and remote characters.
      players.forEach((player, index) => {
        player.setDepth(PLAYER_DEPTH_BASE + index * PLAYER_DEPTH_STEP);
      });
    }
  }

  requestAnimationFrame(sortPlayersByFeet);
};

requestAnimationFrame(sortPlayersByFeet);
