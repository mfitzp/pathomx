import pandas as pd


df = pd.read_csv(config['filename'], delimiter='\t')

_FILTER_PROBABILITIES = df['Localization prob'] >= 0.75
df = df[_FILTER_PROBABILITIES]

labels = ['Leading proteins', 'Amino acid', 'Position']
substitutions = {'Leading proteins': 'Gene names'}
other_indices = ['Multiplicity']

labels_l = len(labels)

labels.extend( substitutions.values())

subs_ix = {labels.index(s): labels.index(t) for s, t in substitutions.items()}

la = []
for args in zip(*[df[l] for l in labels]):
    ol = []
    for n, a in enumerate(args[:labels_l]):
        if a:
            ol.append(str(a))
        elif n in subs_ix:
             ol.append(str( args[subs_ix[n]]))
    
    la.append('-'.join(ol))

df['UniqueLabel'] = la
df.set_index(['UniqueLabel'] + other_indices, inplace=True)
df = df.filter(regex='^([MLH]/[MLH] \d\w)$', axis=1)

# Add the reverse ratios
for a,b in [('H','L'), ('H','M'), ('M','L')]:
    ds = df.filter(regex='%s/%s' % (a,b) )
    ds.columns = pd.Index([l.replace('%s/%s' % (a,b),'%s/%s' % (b,a)) for l in ds.columns.values])
    df = pd.concat([df, 1.0/ ds], axis=1)

df = df.T


classes = [c[:3] for c in df.index.values]
df.index = pd.MultiIndex.from_tuples(zip(df.index.values,classes), names=['Label', 'Class'])

output_data = df
df = None

from pathomx.figures import histogram
Histogram = histogram(output_data)