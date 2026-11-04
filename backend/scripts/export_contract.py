"""Export source-derived API and schema inventories without opening the database."""
import json
from pathlib import Path
from app.main import app
from app.models import Base
from app.core.config import REPOSITORY_ROOT
from app.services.auth_service import STUDENT_ROUTES


def main():
    directory=REPOSITORY_ROOT/'docs'
    schema=app.openapi()
    (directory/'API_CONTRACT.json').write_text(json.dumps(schema,indent=2)+'\n')
    lines=['# Source-derived API inventory','','Credential mode applies a global session/CSRF/role/class dependency.','Local demo mode is explicitly self-asserted. This inventory describes definitions;','runtime evidence is in FINAL_IMPLEMENTATION_REPORT.md.','','| Method | Path | Request / response schema | Access |','|---|---|---|---|']
    for route in app.routes:
        if not getattr(route,'methods',None) or not getattr(route,'include_in_schema',False):continue
        public=route.path.startswith('/health') or route.path in {'/api/auth/config','/api/auth/login'}
        access='public' if public else 'own student/class teacher' if route.name in STUDENT_ROUTES else 'authorized teacher/class'
        entry=schema.get('paths',{}).get(route.path,{})
        for method in sorted(route.methods):
            operation=entry.get(method.lower(),{})
            refs=[]
            def walk(node):
                if isinstance(node,dict):
                    if '$ref' in node:refs.append(node['$ref'].split('/')[-1])
                    for v in node.values():walk(v)
                elif isinstance(node,list):
                    for v in node:walk(v)
            walk(operation.get('requestBody',{}));walk(operation.get('responses',{}))
            lines.append(f'| {method} | `{route.path}` | {", ".join(dict.fromkeys(refs)) or "JSON"} | {access} |')
    (directory/'API_INVENTORY.md').write_text('\n'.join(lines)+'\n')
    lines=['# Source-derived database inventory','','Alembic is canonical. No student data was read for this inventory.','','| Table | Columns | Foreign keys | Constraints |','|---|---|---|---|']
    for table in Base.metadata.sorted_tables:
        columns=', '.join(f'{c.name} ({c.type}{" nullable" if c.nullable else ""})' for c in table.columns)
        fks=', '.join(f'{f.parent.name} → {f.target_fullname}' for f in table.foreign_keys)
        constraints=', '.join(str(c.name or type(c).__name__) for c in table.constraints)
        lines.append(f'| {table.name} | {columns} | {fks} | {constraints} |')
    (directory/'DATABASE_INVENTORY.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
