"""Separate HTTP reachability from usable event collection."""
from collections import Counter


def source_health(source):
    reasons=[]
    if not source.get('ok'):
        return {'status':'unavailable','reasons':[source.get('error') or 'Fonte indisponível']}
    errors=len(source.get('detailErrors',[]))
    if errors:reasons.append(f'{errors} página(s) com erro')
    if source.get('truncated'):reasons.append('Consulta parcial; páginas rodam nas próximas recolhas')
    if source.get('reviewNeeded'):reasons.append('Necessita de revisão manual')
    posters=sum(p.get('status')=='needs-review' for p in source.get('posterCandidates',[]))
    if posters:reasons.append(f'{posters} cartaz(es) por rever')
    if source.get('readMode')=='family-outings':
        count=source.get('outingsCount',0)
        reasons.append(f'{count} passeio(s) verificado(s)')
    elif source.get('readMode')=='public-json':
        count=source.get('eligibleSessions',0)
        reasons.append(f'{count} sessão(ões) elegível(eis) no catálogo público')
    else:
        count=source.get('parsedSessions',0)
        reasons.append(f'{count} sessão(ões) extraída(s) nesta recolha')
    if source.get('reviewNeeded') or posters:status='review-needed'
    elif errors or source.get('truncated'):status='partial'
    elif count:status='collected'
    elif source.get('relevantLinks'):status='discovery-only'
    else:status='no-sessions'
    return {'status':status,'reasons':reasons}


def annotate_sources(sources):
    for source in sources.values():source['collectionHealth']=source_health(source)


def health_summary(sources):
    return dict(Counter(source['collectionHealth']['status'] for source in sources.values()))
