// Injected page extractor (chrome.scripting.executeScript, files: [...]).
// The file's completion value must be the page object, so everything runs in
// one final IIFE expression. Strip chrome → main-content fallback → innerText
// cleanup with the source's character caps.

(() => {
  const clone = document.documentElement.cloneNode(true);
  clone
    .querySelectorAll("script, style, noscript, svg, canvas, iframe, nav, footer, aside, form")
    .forEach((el) => el.remove());

  const root =
    clone.querySelector("article") ||
    clone.querySelector("main") ||
    clone.querySelector("[role=main]") ||
    clone.body ||
    clone;

  const descriptionMeta =
    document.querySelector('meta[name="description"]') ||
    document.querySelector('meta[property="og:description"]');

  const text = (root.innerText || "")
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
    .slice(0, 140000);

  return {
    title: document.title || "",
    url: location.href,
    description: (descriptionMeta && descriptionMeta.content) || "",
    selection: "",
    text,
  };
})()

