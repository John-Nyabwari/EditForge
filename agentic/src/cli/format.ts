const ansi = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  italic: "\x1b[3m",
  black: "\x1b[30m",
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  magenta: "\x1b[35m",
  cyan: "\x1b[36m",
  white: "\x1b[37m",
  bgBlack: "\x1b[40m",
  bgRed: "\x1b[41m",
  bgGreen: "\x1b[42m",
  bgYellow: "\x1b[43m",
  bgBlue: "\x1b[44m",
  bgMagenta: "\x1b[45m",
  bgCyan: "\x1b[46m",
  bgWhite: "\x1b[47m",
};

function t(s: string, ...styles: string[]): string {
  return styles.join("") + s + ansi.reset;
}

export function bold(s: string): string {
  return t(s, ansi.bold);
}

export function dim(s: string): string {
  return t(s, ansi.dim);
}

export function italic(s: string): string {
  return t(s, ansi.italic);
}

export function cyan(s: string): string {
  return t(s, ansi.cyan);
}

export function green(s: string): string {
  return t(s, ansi.green);
}

export function yellow(s: string): string {
  return t(s, ansi.yellow);
}

export function red(s: string): string {
  return t(s, ansi.red);
}

export function magenta(s: string): string {
  return t(s, ansi.magenta);
}

export function blue(s: string): string {
  return t(s, ansi.blue);
}

export function white(s: string): string {
  return t(s, ansi.white);
}

export function header(text: string): string {
  const line = "━".repeat(Math.min(text.length + 4, 60));
  return (
    "\n" +
    t(` ${line}`, ansi.cyan, ansi.bold) + "\n" +
    t(`  ${text}  `, ansi.cyan, ansi.bold) + "\n" +
    t(` ${line}`, ansi.cyan, ansi.bold) + "\n"
  );
}

export function subheader(text: string): string {
  return "\n" + t(`▸ ${text}`, ansi.cyan, ansi.bold) + "\n";
}

export function success(text: string): string {
  return t("  ◆ ", ansi.green) + t(text, ansi.bold);
}

export function info(text: string): string {
  return t("  · ", ansi.dim) + dim(text);
}

export function warn(text: string): string {
  return t("  ◆ ", ansi.yellow) + t(text, ansi.yellow);
}

export function error(text: string): string {
  return t("  ◆ ", ansi.red) + t(text, ansi.red, ansi.bold);
}

export function done(text: string): string {
  return t("  ◆ ", ansi.green) + t(text, ansi.green, ansi.bold);
}

export function item(label: string, detail?: string): string {
  const parts = [t("  · ", ansi.dim) + t(label, ansi.bold)];
  if (detail) parts.push(dim(" " + detail));
  return parts.join("");
}

export function divider(): string {
  return dim("  ─" + "──".repeat(28));
}

export function badge(text: string, color: "green" | "yellow" | "red" | "blue" | "cyan" | "magenta"): string {
  const bg = {
    green: ansi.bgGreen,
    yellow: ansi.bgYellow,
    red: ansi.bgRed,
    blue: ansi.bgBlue,
    cyan: ansi.bgCyan,
    magenta: ansi.bgMagenta,
  }[color];
  const fg = color === "yellow" ? ansi.black : ansi.white;
  return t(` ${text} `, bg, fg, ansi.bold);
}

export function table(rows: string[][], headers?: string[]): string {
  if (rows.length === 0) return "";
  const colCount = rows[0].length;
  const colWidths: number[] = Array(colCount).fill(0);
  const allRows = headers ? [headers, ...rows] : rows;

  for (const row of allRows) {
    for (let i = 0; i < row.length; i++) {
      const raw = row[i].replace(/\x1b\[[0-9;]*m/g, "");
      if (raw.length > colWidths[i]) colWidths[i] = raw.length;
    }
  }

  const sep = "  " + colWidths.map((w) => "─".repeat(w + 2)).join("┬") + "  ";

  let out = "";
  if (headers) {
    out +=
      "  " +
      headers
        .map((h, i) => " " + bold(h) + " ".repeat(colWidths[i] - h.length + 1))
        .join("│") +
      "\n";
    out += dim(sep) + "\n";
  }

  for (const row of rows) {
    out +=
      "  " +
      row
        .map((cell, i) => {
          const raw = cell.replace(/\x1b\[[0-9;]*m/g, "");
          return " " + cell + " ".repeat(colWidths[i] - raw.length + 1);
        })
        .join("│") +
      "\n";
  }

  return out;
}

export function box(text: string, title?: string): string {
  const lines = text.split("\n");
  const contentWidth = Math.max(
    ...lines.map((l) => l.replace(/\x1b\[[0-9;]*m/g, "").length),
    title ? title.length + 4 : 0
  );
  const w = contentWidth + 4;

  let out = "";
  if (title) {
    out += t("┌─", ansi.dim) + t(` ${title} `, ansi.bold) + t("─".repeat(Math.max(0, w - title.length - 5)), ansi.dim) + t("─┐", ansi.dim) + "\n";
  } else {
    out += t("┌" + "─".repeat(w - 2) + "┐", ansi.dim) + "\n";
  }
  for (const line of lines) {
    const raw = line.replace(/\x1b\[[0-9;]*m/g, "");
    out += t("│ ", ansi.dim) + line + " ".repeat(w - raw.length - 4) + t(" │", ansi.dim) + "\n";
  }
  out += t("└" + "─".repeat(w - 2) + "┘", ansi.dim);
  return out;
}

export class Spinner {
  private frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
  private interval: ReturnType<typeof setInterval> | null = null;
  private current = 0;
  private message = "";

  start(message: string): void {
    this.message = message;
    this.current = 0;
    if (process.stdout.isTTY) {
      this.interval = setInterval(() => {
        this.current = (this.current + 1) % this.frames.length;
        process.stdout.write(`\r${t(this.frames[this.current], ansi.cyan)} ${dim(this.message)}`);
      }, 80);
      process.stdout.write(`\r${t(this.frames[0], ansi.cyan)} ${dim(this.message)}`);
    } else {
      console.log(`  ${this.message}...`);
    }
  }

  stop(message?: string): void {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
    if (process.stdout.isTTY) {
      process.stdout.write("\r\x1b[K");
    }
    if (message) {
      console.log(message);
    }
  }

  succeed(text: string): void {
    this.stop(done(text));
  }

  fail(text: string): void {
    this.stop(error(text));
  }
}

export function progressBar(current: number, total: number, width = 24): string {
  const pct = total > 0 ? Math.min(current / total, 1) : 0;
  const filled = Math.round(pct * width);
  const empty = width - filled;
  const bar = t("█".repeat(filled), ansi.cyan) + dim("░".repeat(empty));
  const pctStr = `${Math.round(pct * 100)}%`.padStart(4);
  return `${bar} ${dim(pctStr)}`;
}

export function label(text: string): string {
  return t(text, ansi.cyan, ansi.bold);
}

export function value(text: string): string {
  return t(text, ansi.white);
}
