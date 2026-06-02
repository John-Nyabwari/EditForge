import { execSync } from "node:child_process";
import { header, bold, dim, cyan, green, label, value, box } from "./format";

export async function metadata() {
  const now = new Date();
  const dateTimeTz = now.toLocaleString("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZoneName: "short",
    hour12: false
  }).replace(",", "");
  
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const filenameTz = `${year}-${month}-${day}`;
  
  let gitCommit = "";
  let gitBranch = "";
  let repoName = "";
  
  try {
    execSync("git rev-parse --is-inside-work-tree", { stdio: "ignore" });
    const repoRoot = execSync("git rev-parse --show-toplevel", { encoding: "utf8" }).trim();
    repoName = repoRoot.split("/").pop() || "";
    try {
      gitBranch = execSync("git branch --show-current", { encoding: "utf8" }).trim();
    } catch {
      gitBranch = execSync("git rev-parse --abbrev-ref HEAD", { encoding: "utf8" }).trim();
    }
    gitCommit = execSync("git rev-parse HEAD", { encoding: "utf8" }).trim();
  } catch {
  }
  
  console.log(header("Agentic Metadata"));
  console.log(`  ${dim("Date/Time:")}  ${value(dateTimeTz)}`);
  if (repoName) console.log(`  ${dim("Repo:")}      ${value(repoName)}`);
  if (gitBranch) console.log(`  ${dim("Branch:")}    ${value(gitBranch)}`);
  if (gitCommit) console.log(`  ${dim("Commit:")}   ${dim(gitCommit.substring(0, 12))}`);
  console.log(`\n  ${dim("<!-- XML metadata for research docs -->")}`);
  if (gitCommit) console.log(`  <git_commit>${gitCommit}</git_commit>`);
  if (gitBranch) console.log(`  <branch>${gitBranch}</branch>`);
  if (repoName) console.log(`  <repository>${repoName}</repository>`);
  console.log(`  <last_updated>${filenameTz}</last_updated>`);
  console.log(`  <date>${filenameTz}</date>`);
  console.log();
}