const PLAYER_DEPTH_BASE = 10;
const PLAYER_DEPTH_STEP = 0.01;
const Y_TIE_EPSILON = 1;

const isPlayerContainer = (child: any) =>
  !!child && typeof child.getData === "function" && !!child.getData("sprite");

const sortPlayersByFeet = () => {
  const game = (window as any).__summerEnd3pmGame;

  if (game?.scene?.getScenes) {
    for (const scene of game.scene.getScenes(true)) {
      const players = scene.children.list.filter(isPlayerContainer);
      if (players.length < 1) continue;

      const localPlayer = (scene as any).me;

      players.sort((a: any, b: any) => {
        const dy = Number(a.y) - Number(b.y);

        // Normal 2D rule: the character whose feet are lower on screen is in front.
        // Treat sub-pixel / ~1px network interpolation differences as the same row;
        // otherwise a rounded remote coordinate can appear permanently above the
        // local player even when both characters visually occupy the same position.
        if (Math.abs(dy) > Y_TIE_EPSILON) return dy;

        // On the same visual row, keep the controllable local character visible.
        if (a === localPlayer && b !== localPlayer) return 1;
        if (b === localPlayer && a !== localPlayer) return -1;

        const dx = Number(a.x) - Number(b.x);
        if (Math.abs(dx) > 1) return dx;

        return String(a.getData("playerName") ?? "").localeCompare(
          String(b.getData("playerName") ?? "")
        );
      });

      players.forEach((player: any, index: number) => {
        player.setDepth(PLAYER_DEPTH_BASE + index * PLAYER_DEPTH_STEP);
      });
    }
  }

  requestAnimationFrame(sortPlayersByFeet);
};

requestAnimationFrame(sortPlayersByFeet);
