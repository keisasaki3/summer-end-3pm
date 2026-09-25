export const GAME_TITLE = "午後三時、夏の果。";

document.title = GAME_TITLE;

const installLoginBrand = () => {
  const divs = Array.from(document.querySelectorAll<HTMLDivElement>("div"));
  for (const title of divs) {
    if (title.textContent?.trim() !== "夕凪町へ") continue;
    const panel = title.parentElement;
    if (!panel || panel.querySelector("[data-game-brand]")) continue;

    const brand = document.createElement("div");
    brand.dataset.gameBrand = "true";
    brand.textContent = GAME_TITLE;
    Object.assign(brand.style, {
      fontSize: "15px",
      fontWeight: "500",
      letterSpacing: ".08em",
      opacity: ".72",
      marginBottom: "7px",
    } as Partial<CSSStyleDeclaration>);

    panel.insertBefore(brand, title);
  }
};

const observer = new MutationObserver(installLoginBrand);
observer.observe(document.documentElement, { childList: true, subtree: true });
installLoginBrand();
