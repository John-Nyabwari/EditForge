#!/usr/bin/env bun

import { parseArgs } from "util";
import { pull } from "./pull";
import { status } from "./status";
import { metadata } from "./metadata";
import { init } from "./init";
import { config } from "./config";
import packageJson from "../../package.json";
import { bold, dim, cyan, green, yellow, red, error, header, subheader, done, label, value, box } from "./format";

let values: any;
let positionals: string[];

try {
  const parsed = parseArgs({
    args: Bun.argv,
    options: {
      help: {
        type: "boolean",
        short: "h",
        default: false,
      },
      version: {
        type: "boolean",
        default: false,
      },
      global: {
        type: "boolean",
        short: "g",
        default: false,
      },
      "thoughts-dir": {
        type: "string",
      },
      "agent-model": {
        type: "string",
      },
      "ignore-frontmatter": {
        type: "boolean",
        default: false,
      },
    },
    strict: true,
    allowPositionals: true,
  });
  values = parsed.values;
  positionals = parsed.positionals;
} catch (error: any) {
  if (error.code === "ERR_PARSE_ARGS_UNKNOWN_OPTION") {
    console.error(red(`✗ ${error.message}`));
    console.error(dim("  Run 'agentic --help' for usage information"));
    process.exit(1);
  }
  throw error;
}

const args = positionals.slice(2);
const command = args[0];

if (values.version) {
  console.log(`${cyan("agentic")} ${bold(packageJson.version)}`);
  process.exit(0);
}

if (values.help || command === "help" || !command) {
  console.log(`
${bold(cyan("agentic"))} ${dim("- Manage opencode agents and commands")}

${bold("Usage")}
  ${dim("$")} ${cyan("agentic")} ${green("<command>")} ${dim("[options]")}

${bold("Commands")}
  ${green("init")}     ${dim("[project-path]")}  ${dim("Initialize agentic in a project")}
  ${green("pull")}     ${dim("[project-path]")}  ${dim("Pull agents and commands to .opencode")}
  ${green("status")}   ${dim("[project-path]")}  ${dim("Check which files are up-to-date")}
  ${green("config")}   ${dim("[project-path]")}  ${dim("Get or set configuration values")}
  ${green("metadata")}             ${dim("Show project metadata for research docs")}
  ${green("version")}              ${dim("Show the version of agentic")}
  ${green("help")}                 ${dim("Show this help message")}

${bold("Options")}
  ${yellow("-h, --help")}             ${dim("Show this help message")}
  ${yellow("-g, --global")}           ${dim("Use ~/.config/opencode instead of .opencode")}
  ${yellow("--version")}              ${dim("Show the version")}
  ${yellow("--thoughts-dir")}         ${dim("Specify thoughts directory (for init)")}
  ${yellow("--agent-model")}          ${dim("Specify model for subagents")}
  ${yellow("--ignore-frontmatter")}   ${dim("Ignore YAML frontmatter in Markdown")}

${bold("Examples")}
  ${dim("$")} agentic init
  ${dim("$")} agentic init ${dim("~/projects/my-app")}
  ${dim("$")} agentic pull ${dim("~/projects/my-app")}
  ${dim("$")} agentic pull ${yellow("-g")}
  ${dim("$")} agentic status
  ${dim("$")} agentic config ${cyan("agent.model")} ${green("opus-4-1")}
  ${dim("$")} agentic metadata
`);
  process.exit(0);
}

switch (command) {
  case "init":
    const initPath = args[1];
    await init(initPath, values["thoughts-dir"]);
    break;
  case "pull":
  case "status":
    const projectPath = args[1];
    if (values.global && projectPath) {
      console.error(red("✗ Cannot use --global flag with a project path"));
      process.exit(1);
    }

    if (command === "pull") {
      await pull(projectPath, values.global, values["agent-model"], values["ignore-frontmatter"]);
    } else if (command === "status") {
      await status(projectPath, values.global, values["agent-model"], values["ignore-frontmatter"]);
    }
    break;
  case "config":
    const configKey = args[1];
    const configValue = args[2];
    const configProjectPath = args[3];
    await config(configProjectPath, configKey, configValue);
    break;
  case "metadata":
    await metadata();
    break;
  case "version":
    console.log(`${cyan("agentic")} ${bold(packageJson.version)}`);
    break;
  case "help":
    break;
  default:
    console.error(red(`✗ Unknown command '${command}'`));
    console.error(dim("  Run 'agentic --help' for usage information"));
    process.exit(1);
}
