import { mkdir, copyFile, writeFile } from "node:fs/promises";
import { join, dirname } from "node:path";
import { existsSync } from "node:fs";
import { resolveProjectPath, findOutOfSyncFiles, findAgenticInstallDir, processAgentTemplate, resolveAgentModel } from "./utils";
import { header, done, dim, cyan, green, bold, progressBar, Spinner, success, info } from "./format";

function extractYamlFrontmatter(text: string): { frontmatter: string | null, body: string } {
  if (!text.startsWith('---\n') && !text.startsWith('---\r\n')) {
    return { frontmatter: null, body: text };
  }

  const lines = text.split('\n');
  let endIndex = -1;

  for (let i = 1; i < lines.length; i++) {
    if (lines[i].trim() === '---') {
      endIndex = i;
      break;
    }
  }

  if (endIndex === -1) {
    return { frontmatter: null, body: text };
  }

  const frontmatter = lines.slice(0, endIndex + 1).join('\n');
  const body = lines.slice(endIndex + 1).join('\n');

  return { frontmatter, body };
}

function mergeMdPreservingTargetFrontmatter(targetText: string, sourceText: string): string {
  const target = extractYamlFrontmatter(targetText);
  const source = extractYamlFrontmatter(sourceText);

  if (target.frontmatter) {
    return target.frontmatter + '\n' + source.body;
  } else {
    return source.body;
  }
}

export async function pull(
  projectPath: string | undefined,
  useGlobal: boolean = false,
  agentModel?: string,
  ignoreFrontmatter: boolean = false,
) {
  const resolvedProjectPath = resolveProjectPath(projectPath, useGlobal);

  const targetBase = useGlobal
    ? resolvedProjectPath
    : join(resolvedProjectPath, ".opencode");

  const resolvedModel = await resolveAgentModel(agentModel, resolvedProjectPath);

  const syncStatus = await findOutOfSyncFiles(targetBase, agentModel, resolvedProjectPath, ignoreFrontmatter);
  const sourceDir = findAgenticInstallDir();

  const filesToCopy = syncStatus.filter(f => f.status === 'missing' || f.status === 'outdated');

  console.log(header("Agentic Pull"));
  console.log(`  ${dim(cyan("⟫"))} ${dim("Target:")} ${bold(targetBase)}\n`);

  if (filesToCopy.length === 0) {
    console.log(`  ${done("All files are up-to-date")}\n`);
    return;
  }

  console.log(`  ${info(`Found ${bold(String(filesToCopy.length))} file${filesToCopy.length === 1 ? "" : "s"} to update`)}`);

  for (let i = 0; i < filesToCopy.length; i++) {
    const file = filesToCopy[i];
    const sourceFile = join(sourceDir, file.path);
    const targetFile = join(targetBase, file.path);
    const targetDir = dirname(targetFile);

    if (!existsSync(targetDir)) {
      await mkdir(targetDir, { recursive: true });
    }

    const isAgentMarkdown = file.path.startsWith('agent/') && file.path.endsWith('.md');
    const isMarkdown = file.path.endsWith('.md');

    if (isAgentMarkdown) {
      const sourceContent = await processAgentTemplate(sourceFile, resolvedModel);
      if (file.status === 'missing') {
        await writeFile(targetFile, sourceContent, 'utf-8');
      } else if (ignoreFrontmatter && isMarkdown && file.status === 'outdated') {
        const targetText = await Bun.file(targetFile).text();
        const merged = mergeMdPreservingTargetFrontmatter(targetText, sourceContent);
        await writeFile(targetFile, merged, 'utf-8');
      } else {
        await writeFile(targetFile, sourceContent, 'utf-8');
      }
    } else if (ignoreFrontmatter && isMarkdown && file.status === 'outdated') {
      const sourceText = await Bun.file(sourceFile).text();
      const targetText = await Bun.file(targetFile).text();
      const merged = mergeMdPreservingTargetFrontmatter(targetText, sourceText);
      await writeFile(targetFile, merged, 'utf-8');
    } else {
      await copyFile(sourceFile, targetFile);
    }

    const pct = progressBar(i + 1, filesToCopy.length);
    const action = file.status === 'missing' ? green("added") : cyan("updated");
    console.log(`  ${pct} ${action} ${dim(file.path)}`);
  }

  console.log(`\n  ${done(`Updated ${bold(String(filesToCopy.length))} file${filesToCopy.length === 1 ? "" : "s"}`)}\n`);
}
