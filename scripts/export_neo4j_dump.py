"""
ShopGraph — Neo4j Aura Migration & Dump Utility
================================================
Assists in migrating the local ShopGraph graph database and vector embeddings
to Neo4j AuraDB Free cloud instances.

Usage Options:
    1. Automated Cloud Sync (Recommended):
       python scripts/export_neo4j_dump.py --sync-to-aura --uri neo4j+s://<id>.databases.neo4j.io --password <pass>

    2. Local Docker Dump Export:
       python scripts/export_neo4j_dump.py --dump-local
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"


def dump_local_docker(output_dir: Path):
    """Executes neo4j-admin dump inside the local docker container."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dump_filename = "neo4j_shopgraph.dump"
    target_path = output_dir / dump_filename

    print("[*] Generating local Neo4j database dump from Docker container 'shopgraph-neo4j'...")
    try:
        # Check if container is running
        res = subprocess.run(["docker", "ps", "--filter", "name=shopgraph-neo4j", "--format", "{{.Names}}"],
                             capture_output=True, text=True, check=True)
        if "shopgraph-neo4j" not in res.stdout:
            print("[!] Container 'shopgraph-neo4j' is not running. Please start it with 'docker compose up -d'.")
            return False

        # Run dump command inside container
        cmd = [
            "docker", "exec", "shopgraph-neo4j",
            "neo4j-admin", "database", "dump", "neo4j",
            f"--to-path=/tmp/"
        ]
        print(f"[*] Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        # Copy dump from container to host
        copy_cmd = ["docker", "cp", f"shopgraph-neo4j:/tmp/neo4j.dump", str(target_path)]
        print(f"[*] Copying dump to: {target_path}")
        subprocess.run(copy_cmd, check=True)

        print(f"[✓] Database dump successfully created at: {target_path}")
        print("[*] You can now upload this file directly into your Neo4j Aura Console:")
        print("    1. Go to https://console.neo4j.io")
        print("    2. Click your AuraDB Free instance -> '...' menu -> 'Load Database'")
        print(f"    3. Select: {target_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Error creating docker dump: {e}")
        return False
    except FileNotFoundError:
        print("[!] Docker executable not found. Ensure Docker Desktop is installed and in PATH.")
        return False


def sync_to_aura(uri: str, user: str, password: str, database: str = "neo4j"):
    """Runs ingestion and vector embedding directly against Neo4j Aura."""
    print(f"[*] Connecting to Neo4j Aura at: {uri}...")
    
    # 1. Ingestion
    ingest_script = ROOT_DIR / "scripts" / "ingest_neo4j.py"
    print(f"[*] Step 1: Ingesting nodes and relationships into Aura...")
    cmd_ingest = [
        sys.executable, str(ingest_script),
        "--uri", uri,
        "--user", user,
        "--password", password,
        "--database", database,
        "--batch-size", "1000",
    ]
    res = subprocess.run(cmd_ingest)
    if res.returncode != 0:
        print("[!] Ingestion into Aura failed.")
        return False

    # 2. Vector Embeddings
    embed_script = ROOT_DIR / "scripts" / "build_embeddings.py"
    print(f"[*] Step 2: Generating BGE-base vector embeddings and building indexes on Aura...")
    # Inject env vars for build_embeddings
    env = os.environ.copy()
    env["NEO4J_URI"] = uri
    env["NEO4J_USERNAME"] = user
    env["NEO4J_PASSWORD"] = password
    env["NEO4J_DATABASE"] = database
    res_embed = subprocess.run([sys.executable, str(embed_script), "--batch-size", "1000"], env=env)
    if res_embed.returncode != 0:
        print("[!] Vector index creation on Aura failed.")
        return False

    print("\n[✓] Neo4j Aura migration and vector indexing complete!")
    return True


def main():
    parser = argparse.ArgumentParser(description="ShopGraph Neo4j Aura Migration Utility")
    parser.add_argument("--dump-local", action="store_true", help="Export local Docker Neo4j into .dump file for Aura console upload")
    parser.add_argument("--sync-to-aura", action="store_true", help="Run ingestion and vector indexing directly to a live Aura instance")
    parser.add_argument("--uri", type=str, default=os.getenv("NEO4J_URI"), help="Neo4j Aura URI (neo4j+s://...)")
    parser.add_argument("--user", type=str, default=os.getenv("NEO4J_USERNAME", "neo4j"), help="Neo4j username")
    parser.add_argument("--password", type=str, default=os.getenv("NEO4J_PASSWORD"), help="Neo4j password")
    parser.add_argument("--output-dir", type=Path, default=ROOT_DIR / "data" / "dumps", help="Directory for exported dump")

    args = parser.parse_args()

    if args.dump_local:
        dump_local_docker(args.output_dir)
    elif args.sync_to_aura:
        if not args.uri or not args.password:
            print("[!] Error: --uri and --password are required for --sync-to-aura.")
            sys.exit(1)
        sync_to_aura(args.uri, args.user, args.password)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
