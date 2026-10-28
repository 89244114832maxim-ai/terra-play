#!/usr/bin/env python3
"""Wait for Pages metadata and prepare an offline package; never publish."""
import json,os,pathlib,re,subprocess,time
from release_package import package

def ready(runs, sha):
    matching=[r for r in runs if r.get('name')=='pages build and deployment' and r.get('event')=='dynamic' and r.get('head_branch')=='main' and r.get('head_sha')==sha]
    if any(r.get('status')=='completed' and r.get('conclusion')=='success' for r in matching):
        return next(r for r in matching if r.get('status')=='completed' and r.get('conclusion')=='success')
    return None

def gh(*args):
    return json.loads(subprocess.check_output(['gh','api',*args],text=True))

def current(repo): return gh(f'repos/{repo}/git/ref/heads/main')['object']['sha']

def main():
    repo=os.environ['GITHUB_REPOSITORY']; sha=os.environ['GITHUB_SHA']; out=pathlib.Path(os.environ['RUNNER_TEMP'])/'terra.zip'
    if not re.fullmatch(r'[0-9a-f]{40}',sha): raise ValueError('invalid commit')
    if subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()!=sha: raise ValueError('checkout mismatch')
    for _ in range(40):
        if current(repo)!=sha: raise ValueError('main changed during wait')
        runs=gh(f'repos/{repo}/actions/runs?per_page=100')['workflow_runs']; match=ready(runs,sha)
        if match:
            jobs=gh(f"repos/{repo}/actions/runs/{match['id']}/jobs?per_page=100")['jobs']
            if not any(j.get('name')=='deploy' and j.get('status')=='completed' and j.get('conclusion')=='success' for j in jobs): raise ValueError('deploy job not confirmed')
            result=package('.',out)
            if current(repo)!=sha: raise ValueError('main changed after packaging')
            print(json.dumps({'pages_run':match['html_url'],'commit':sha,'package':result},ensure_ascii=False)); return
        time.sleep(15)
    raise TimeoutError('successful Pages deployment was not observed')
if __name__=='__main__': main()
