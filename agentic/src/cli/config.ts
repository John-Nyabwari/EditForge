import { join } from "node:path";
import { existsSync, writeFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { resolveProjectPath } from "./utils";
import { header, bold, dim, cyan, green, yellow, red, done, label, value, box, table } from "./format";

interface AgenticConfig {
  thoughts: string;
  agents: {
    model: string;
  };
}

function getDefaultConfig(): AgenticConfig {
  return {
    thoughts: "thoughts",
    agents: {
      model: "opencode/grok-code"
    }
  };
}

async function readConfig(projectPath: string): Promise<AgenticConfig> {
  const configPath = join(projectPath, ".opencode", "agentic.json");

  if (!existsSync(configPath)) {
    return getDefaultConfig();
  }

  try {
    const configContent = await readFile(configPath, 'utf-8');
    const config = JSON.parse(configContent);

    return {
      thoughts: config.thoughts || "thoughts",
      agents: {
        model: config.agents?.model || "opencode/grok-code"
      }
    };
  } catch (error) {
    console.warn(yellow(`Warning: Could not read config at ${configPath}, using defaults`));
    return getDefaultConfig();
  }
}

function writeConfig(projectPath: string, config: AgenticConfig): void {
  const opencodeDir = join(projectPath, ".opencode");
  const configPath = join(opencodeDir, "agentic.json");

  if (!existsSync(opencodeDir)) {
    throw new Error(`No .opencode directory found at ${opencodeDir}. Run 'agentic init' first.`);
  }

  writeFileSync(configPath, JSON.stringify(config, null, 2));
}

function setNestedValue(obj: any, path: string, value: string): void {
  const keys = path.split('.');
  let current = obj;

  if (keys[0] === 'agent' && keys[1] === 'model') {
    keys[0] = 'agents';
  }

  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];
    if (!(key in current) || typeof current[key] !== 'object') {
      current[key] = {};
    }
    current = current[key];
  }

  const finalKey = keys[keys.length - 1];
  current[finalKey] = value;
}

function getNestedValue(obj: any, path: string): string | undefined {
  const keys = path.split('.');

  if (keys[0] === 'agent' && keys[1] === 'model') {
    keys[0] = 'agents';
  }

  let current = obj;
  for (const key of keys) {
    if (!(key in current)) {
      return undefined;
    }
    current = current[key];
  }

  return typeof current === 'string' ? current : undefined;
}

export async function config(projectPath: string | undefined, key?: string, newValue?: string): Promise<void> {
  const resolvedProjectPath = resolveProjectPath(projectPath);
  const currentConfig = await readConfig(resolvedProjectPath);

  if (!key) {
    console.log(header("Agentic Config"));
    const rows = Object.entries(currentConfig).flatMap(([k, v]) => {
      if (typeof v === 'object') {
        return Object.entries(v).map(([sk, sv]) => [label(`${k}.${sk}`), value(String(sv))]);
      }
      return [[label(k), value(String(v))]];
    });
    console.log(table(rows));
    console.log();
    return;
  }

  if (!newValue) {
    const currentValue = getNestedValue(currentConfig, key);
    if (currentValue === undefined) {
      console.log(`  ${yellow("?")} ${dim(`Configuration key '${key}' not found`)}`);
    } else {
      console.log(`  ${label(key)} ${dim("→")} ${value(currentValue)}`);
    }
    return;
  }

  setNestedValue(currentConfig, key, newValue);
  writeConfig(resolvedProjectPath, currentConfig);

  console.log(`  ${done(`${label(key)} ${dim("→")} ${green(newValue)}`)}`);
}
