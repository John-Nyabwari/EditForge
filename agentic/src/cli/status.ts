import { join } from "node:path";
import { resolveProjectPath, findOutOfSyncFiles } from "./utils";
import { header, bold, dim, cyan, green, yellow, red, done, warn, badge, table, divider, label, value } from "./format";

export async function status(
  projectPath: string | undefined,
  useGlobal: boolean = false,
  agentModel?: string,
  ignoreFrontmatter: boolean = false,
) {
  const resolvedProjectPath = resolveProjectPath(projectPath, useGlobal);
  
  const targetBase = useGlobal 
    ? resolvedProjectPath 
    : join(resolvedProjectPath, ".opencode");
  
  const syncStatus = await findOutOfSyncFiles(targetBase, agentModel, resolvedProjectPath, ignoreFrontmatter);
  
  const upToDateCount = syncStatus.filter(f => f.status === 'up-to-date').length;
  const outdatedCount = syncStatus.filter(f => f.status === 'outdated').length;
  const missingCount = syncStatus.filter(f => f.status === 'missing').length;
  
  console.log(header("Agentic Status"));
  console.log(`  ${dim(cyan("⟫"))} ${dim("Target:")} ${bold(targetBase)}\n`);

  if (syncStatus.length === 0) {
    console.log(`  ${warn("No agentic files found")}\n`);
    return;
  }

  const rows: string[][] = [];
  for (const file of syncStatus) {
    const statusBadge = file.status === 'up-to-date'
      ? badge("ok", "green")
      : file.status === 'outdated'
      ? badge("old", "yellow")
      : badge("miss", "red");
    rows.push([statusBadge, dim(file.path)]);
  }

  console.log(table(rows));

  divider();
  console.log(`  ${green(`● ${upToDateCount} up-to-date`)}  ${yellow(`● ${outdatedCount} outdated`)}  ${red(`● ${missingCount} missing`)}`);
  
  const totalIssues = outdatedCount + missingCount;
  if (totalIssues === 0) {
    console.log(`\n  ${done("All agentic files are up-to-date")}\n`);
  } else {
    console.log(`\n  ${warn(`${bold(String(totalIssues))} file${totalIssues === 1 ? "" : "s"} need${totalIssues === 1 ? "s" : ""} updating`)}`);
    console.log(`  ${dim("Run")} ${cyan("agentic pull")} ${dim("to sync the files")}\n`);
  }
}