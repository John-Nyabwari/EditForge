import { join, resolve } from "node:path";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import * as readline from "node:readline/promises";
import { stdin as input, stdout as output } from "node:process";
import { header, success, info, done, yellow, dim, cyan, bold, label, value, box, Spinner } from "./format";

interface AgenticConfig {
  thoughts: string;
  agents: {
    model: string;
  };
}

export async function init(projectPath?: string, thoughtsDirOverride?: string): Promise<void> {
  const isInteractive = !thoughtsDirOverride;
  const rl = isInteractive ? readline.createInterface({ input, output }) : null;
  
  try {
    const targetPath = projectPath ? resolve(projectPath) : process.cwd();
    const opencodeDir = join(targetPath, ".opencode");
    const configPath = join(opencodeDir, "agentic.json");
    
    if (existsSync(configPath)) {
      if (isInteractive && rl) {
        const overwrite = await rl.question(
          `${yellow("?")} ${bold("Already initialized. Reinitialize?")} ${dim("(y/N):")} `
        );
        
        if (overwrite.toLowerCase() !== "y") {
          console.log(`  ${dim("Initialization cancelled.")}`);
          return;
        }
      } else {
        console.log(`  ${dim("Already initialized. Reinitializing...")}`);
      }
    }
    
    console.log(header("Agentic Init"));
    console.log(`  ${dim(cyan("⟫"))} ${dim("Setting up project:")} ${bold(targetPath)}\n`);
    
    const spinner = new Spinner();
    
    spinner.start("Creating .opencode directory");
    if (!existsSync(opencodeDir)) {
      mkdirSync(opencodeDir, { recursive: true });
    }
    spinner.succeed(done("Created .opencode directory"));
    
    let thoughtsDir: string;
    if (thoughtsDirOverride) {
      thoughtsDir = thoughtsDirOverride;
    } else if (rl) {
      const defaultThoughtsDir = "thoughts";
      const thoughtsPrompt = `  ${cyan("?")} ${bold("Thoughts directory name?")} ${dim(`(default: ${defaultThoughtsDir}):`)} `;
      const thoughtsInput = await rl.question(thoughtsPrompt);
      thoughtsDir = thoughtsInput.trim() || defaultThoughtsDir;
    } else {
      thoughtsDir = "thoughts";
    }
    
    const thoughtsPath = join(targetPath, thoughtsDir);
    
    const thoughtsSubDirs = [
      "architecture",
      "tickets", 
      "research",
      "plans",
      "reviews"
    ];
    
    spinner.start(`Creating ${thoughtsDir}/ directory structure`);
    if (!existsSync(thoughtsPath)) {
      mkdirSync(thoughtsPath, { recursive: true });
    }
    for (const subDir of thoughtsSubDirs) {
      const subDirPath = join(thoughtsPath, subDir);
      if (!existsSync(subDirPath)) {
        mkdirSync(subDirPath, { recursive: true });
      }
    }
    spinner.succeed(done(`Created ${thoughtsDir}/ directory structure`));
    
    const config: AgenticConfig = {
      thoughts: thoughtsDir,
      agents: {
        model: "sonic-fast"
      }
    };
    
    writeFileSync(configPath, JSON.stringify(config, null, 2));
    console.log(success("Created agentic.json configuration"));
    
    const readmePath = join(thoughtsPath, "README.md");
    if (!existsSync(readmePath)) {
      const readmeContent = `# Thoughts Directory\n\nThis directory contains structured documentation for your project:\n\n## Directory Structure\n\n- **architecture/** - System architecture documentation and design decisions\n- **tickets/** - Task tickets, feature requests, and bug reports\n- **research/** - Research notes, investigations, and findings\n- **plans/** - Project plans, roadmaps, and implementation strategies\n- **reviews/** - Code reviews, retrospectives, and assessments\n\n## Usage\n\nThese directories are used by Agentic to organize and retrieve contextual information about your project.\n`;
      writeFileSync(readmePath, readmeContent);
      console.log(success(`Created ${thoughtsDir}/README.md`));
    }
    
    console.log(`\n${bold(cyan("  ◆  Agentic initialization complete!"))}\n`);
    console.log(`  ${dim("Config:")}   ${value(configPath)}`);
    console.log(`  ${dim("Thoughts:")} ${value(thoughtsPath)}`);
    console.log();
    
  } finally {
    if (rl) {
      rl.close();
    }
  }
}