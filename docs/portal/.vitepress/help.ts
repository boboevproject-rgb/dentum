/**
 * Build-time generator for the in-app help fragments (Fase 5).
 *
 * After VitePress finishes building, we walk every screen markdown file
 * under `docs/user-manual/<lang>/<module>/screens/*.md`, render its body
 * with markdown-it, and emit a standalone HTML fragment at
 * `dist/<lang>/help/<route-slug>.html`. The frontend `<HelpButton />`
 * drawer points an iframe at this URL.
 *
 * Slug from route:
 *   /patients               → patients
 *   /patients/[id]          → patients_[id]
 *   /settings/verifactu/queue → settings_verifactu_queue
 *   /                       → index
 */
import { mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, resolve } from "node:path";
import MarkdownIt from "markdown-it";

const HERE = fileURLToPath(new URL(".", import.meta.url));
// docs/portal/.vitepress/ → /docs/.
const DOCS_ROOT = resolve(HERE, "..", "..");
const USER_MANUAL_ROOT = join(DOCS_ROOT, "user-manual");

const LOCALES = ["en", "es"] as const;

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: false,
});

interface Frontmatter {
  module?: string;
  route?: string;
  screen?: string;
  [key: string]: unknown;
}

function parseFrontmatter(text: string): { fm: Frontmatter; body: string } {
  if (!text.startsWith("---")) return { fm: {}, body: text };
  const end = text.indexOf("\n---", 3);
  if (end === -1) return { fm: {}, body: text };
  const block = text.slice(3, end).trim();
  const body = text.slice(end + 4).replace(/^\s*\n/, "");
  const fm: Frontmatter = {};
  let listKey: string | null = null;
  for (const raw of block.split("\n")) {
    if (!raw.trim() || raw.trimStart().startsWith("#")) continue;
    if (raw.startsWith("  - ")) {
      if (!listKey) continue;
      const arr = (fm[listKey] as string[] | undefined) ?? [];
      arr.push(raw.slice(4).trim().replace(/^["']|["']$/g, ""));
      fm[listKey] = arr;
      continue;
    }
    if (raw.startsWith("- ")) continue;
    const colon = raw.indexOf(":");
    if (colon === -1) continue;
    const key = raw.slice(0, colon).trim();
    const value = raw.slice(colon + 1).trim();
    if (value === "") {
      listKey = key;
      fm[key] = [];
    } else {
      listKey = null;
      fm[key] = value.replace(/^["']|["']$/g, "");
    }
  }
  return { fm, body };
}

export function routeToSlug(route: string): string {
  const [pathOnly = "", query = ""] = route.split(/[?#]/, 2)
  const segments = pathOnly
    .replace(/^\/+|\/+$/g, "")
    .split("/")
    .filter(Boolean)
    .map((segment) =>
      /^\{[^}]+\}$/.test(segment) || /^\[[^\]]+\]$/.test(segment) || /^:[A-Za-z0-9_]+$/.test(segment)
        ? "id"
        : segment,
    )
  const pathSlug = segments.length ? segments.join("_") : "index"
  const querySlug = [...new URLSearchParams(query).entries()]
    .sort(([ak, av], [bk, bv]) => ak === bk ? (av < bv ? -1 : av > bv ? 1 : 0) : ak < bk ? -1 : 1)
    .map(([key, value]) => `${key}_${value}`)
    .join("_")
    .replace(/[^A-Za-z0-9_-]/g, "_")
  return querySlug ? `${pathSlug}__${querySlug}` : pathSlug
}

async function collectScreens(): Promise<
  Array<{ locale: string; module: string; route: string; body: string; file: string }>
> {
  const out: Array<{
    locale: string;
    module: string;
    route: string;
    body: string;
    file: string;
  }> = [];

  for (const locale of LOCALES) {
    const localeRoot = join(USER_MANUAL_ROOT, locale);
    if (!existsSync(localeRoot)) continue;
    const moduleEntries = await readdir(localeRoot, { withFileTypes: true });
    for (const moduleEntry of moduleEntries) {
      if (!moduleEntry.isDirectory()) continue;
      const screensDir = join(localeRoot, moduleEntry.name, "screens");
      if (!existsSync(screensDir)) continue;
      const screenFiles = await readdir(screensDir);
      for (const name of screenFiles) {
        if (!name.endsWith(".md")) continue;
        const filePath = join(screensDir, name);
        const text = await readFile(filePath, "utf-8");
        const { fm, body } = parseFrontmatter(text);
        if (!fm.route || typeof fm.route !== "string") continue;
        out.push({
          locale,
          module: moduleEntry.name,
          route: fm.route,
          body,
          file: filePath,
        });
      }
    }
  }

  return out;
}

const FRAGMENT_SHELL = (locale: string, title: string, body: string): string => `<!doctype html>
<html lang="${locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${escapeHtml(title)}</title>
<link rel="stylesheet" href="../../help-fragment.css">
</head>
<body class="help-fragment">
<article>
${body}
</article>
</body>
</html>
`;

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const NOT_FOUND_BY_LOCALE: Record<string, { title: string; body: string }> = {
  en: {
    title: "Dentum Help Center",
    body: `<h1>Dentum Help Center</h1>
<p>Browse the user guide for step-by-step instructions for clinic setup,
patients, appointments, clinical records, billing, and administration.</p>
<p><a href="../../user-manual/en/">Open the Dentum user manual</a></p>
<p>Use the manual search or choose a topic from its navigation to find the
instructions you need.</p>`,
  },
  es: {
    title: "Centro de ayuda de Dentum",
    body: `<h1>Centro de ayuda de Dentum</h1>
<p>Consulta la guía de usuario para ver instrucciones paso a paso sobre la
configuración de la clínica, pacientes, citas, historiales clínicos,
facturación y administración.</p>
<p><a href="../../user-manual/es/">Abrir el manual de usuario de Dentum</a></p>
<p>Utiliza la búsqueda del manual o elige un tema en la navegación para
encontrar las instrucciones que necesitas.</p>`,
  },
};

export async function buildHelpFragments(distDir: string): Promise<number> {
  const screens = await collectScreens();
  let written = 0;

  // Two screens whose routes collapse to the same slug write the same
  // file, and the last one silently wins (#573). That is a real trap
  // here: the obvious "fix" for the periodontogram route -- changing
  // `{id}` to `[id]` -- would make it collide with the patient-detail
  // doc, and the patient page would lose its help with nothing to show
  // that it had happened. Fail the build instead.
  // Paths relative to `docs/`, so the message reads the same locally and
  // on a CI runner.
  const rel = (file: string) => file.replace(`${DOCS_ROOT}/`, "");
  const byTarget = new Map<string, Array<{ file: string; route: string }>>();
  for (const screen of screens) {
    const key = `${screen.locale}/${routeToSlug(screen.route)}`;
    const bucket = byTarget.get(key) ?? [];
    bucket.push({ file: rel(screen.file), route: screen.route });
    byTarget.set(key, bucket);
  }
  const collisions = [...byTarget.entries()].filter(([, v]) => v.length > 1);
  if (collisions.length > 0) {
    const detail = collisions
      .map(([key, v]) =>
        [
          `  ${key}.html would be written by ${v.length} screens:`,
          ...v.map((x) => `    ${x.file}  (route: ${x.route})`),
        ].join("\n"),
      )
      .join("\n");
    throw new Error(
      `Help fragment slug collision: two or more screens map to the same ` +
        `file, so one would overwrite the other.\n${detail}\n` +
        `Give each screen a route that collapses to a distinct slug.`,
    );
  }

  for (const screen of screens) {
    const slug = routeToSlug(screen.route);
    const outDir = join(distDir, screen.locale, "help");
    await mkdir(outDir, { recursive: true });
    const html = md.render(screen.body);
    // First H1 in the body is the title; fall back to module + route.
    const titleMatch = screen.body.match(/^#\s+(.+)$/m);
    const title = titleMatch
      ? titleMatch[1].trim()
      : `${screen.module} — ${screen.route}`;
    const out = FRAGMENT_SHELL(screen.locale, title, html);
    await writeFile(join(outDir, `${slug}.html`), out, "utf-8");
    written++;
  }

  // Per-locale fallback fragment served by nginx when no specific file
  // matches the requested route. Keeps the iframe's HTTP status at 200
  // so the in-app drawer renders a friendly message instead of nginx's
  // raw 404 page.
  for (const locale of LOCALES) {
    const outDir = join(distDir, locale, "help");
    await mkdir(outDir, { recursive: true });
    const data = NOT_FOUND_BY_LOCALE[locale];
    const out = FRAGMENT_SHELL(locale, data.title, data.body);
    await writeFile(join(outDir, "_not-found.html"), out, "utf-8");
  }

  return written;
}
