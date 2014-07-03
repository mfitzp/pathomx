'''
Initialise the biocyc database interface with the standard set of human metabolic
pathways. Should find somewhere better to put this (distribute with biocyc itself?)
'''

from biocyc import biocyc
biocyc.set_organism('HUMAN')
DEFAULT_PATHWAYS = ["PWY-5340", "PWY-5143", "PWY-5754", "PWY-6482", "PWY-5905",
        "SER-GLYSYN-PWY-1", "PWY-4983", "ASPARAGINE-BIOSYNTHESIS", "ASPARTATESYN-PWY",
        "PWY-3982", "PWY-6292", "HOMOCYSDEGR-PWY", "GLUTAMATE-SYN2-PWY", "PWY-5921",
        "GLNSYN-PWY", "GLYSYN-PWY", "GLYSYN-ALA-PWY", "ADENOSYLHOMOCYSCAT-PWY",
        "PWY-6755", "ARGININE-SYN4-PWY", "PWY-5331", "PWY-4921", "PROSYN-PWY",
        "SERSYN-PWY", "PWY-6281", "TRNA-CHARGING-PWY", "PWY66-399", "PWY-6138",
        "PWY-5659", "PWY-66", "PWY-6", "PWY-5661-1", "PWY-4821",
        "MANNOSYL-CHITO-DOLICHOL-BIOSYNTHESIS", "PWY-5067", "PWY-6564", "PWY-6568",
        "PWY-6558", "PWY-6567", "PWY-6571", "PWY-6557", "PWY-6566", "PWY-6569",
        "PWY-5512", "PWY-5514", "PWY-5963", "PWY-6012-1", "PWY-7250", "SAM-PWY",
        "COA-PWY-1", "PWY0-522", "PWY0-1275", "PWY-6823", "NADPHOS-DEPHOS-PWY-1",
        "NADSYN-PWY", "NAD-BIOSYNTHESIS-III", "PWY-5653", "PWY-5123", "PWY-5910",
        "PWY-5120", "PWY-5920", "HEME-BIOSYNTHESIS-II", "PWY-5872", "PWY-4041",
        "GLUTATHIONESYN-PWY", "THIOREDOX-PWY", "GLUT-REDOX-PWY", "PWY-4081", "PWY-5663",
        "PWY-5189", "PWY-6076", "PWY-2161", "PWY-2161B", "PWY-2201", "PWY-6613",
        "PWY-6872", "PWY-6857", "PWY-6875", "PWY-6861", "PWY66-366", "PWY-6898",
        "PLPSAL-PWY", "PWY-6030", "PWY-6241", "PWY-7299", "PWY-7305", "PWY-7306",
        "PWY66-301", "PWY66-374", "PWY66-375", "PWY66-377", "PWY66-378", "PWY66-380",
        "PWY66-381", "PWY66-382", "PWY66-392", "PWY66-393", "PWY66-394", "PWY66-395",
        "PWY66-397", "PWY-5148", "PWY-6129", "PWY0-1264", "PWY3DJ-11281", "TRIGLSYN-PWY",
        "FASYN-ELONG-PWY", "PWY-5966-1", "PWY-6000", "PWY-5996", "PWY-5994", "PWY-5972",
        "PWY-7049", "PWY-6352", "PWY-6367", "PWY-6371", "PWY-7501", "PWY-5667",
        "PWY-5269", "PWY3O-450", "PWY4FS-6", "PWY3DJ-12", "PWY-6061", "PWY-6074",
        "PWY-6132", "PWY-7455", "PWY66-3", "PWY66-341", "PWY66-4", "PWY66-5",
        "PWY-6158", "PWY-6100", "PWY-6405", "PWY66-420", "PWY66-423", "PWY66-421",
        "PWY66-385", "PWY-7227", "PWY-7226", "PWY-7184", "PWY-7211", "PWY-6689",
        "PWY-7375-1", "PWY-7286", "PWY-7283", "PWY-6121", "PWY-7228", "PWY-841",
        "PWY-7219", "PWY-7221", "PWY-6124", "PWY-7224", "PWY66-409", "P121-PWY",
        "PWY-6619", "PWY-6609", "PWY-6620", "PWY-7176", "PWY-5686", "PWY0-162",
        "PWY-7210", "PWY-7197", "PWY-7199", "PWY-7205", "PWY-7193", "PWY-7200",
        "PWY-5389", "PWY-5670", "PWY-6481", "PWY-6498", "PWY66-425", "PWY66-426",
        "PWY0-662", "PWY-5695", "ARGSPECAT-PWY", "GLYCGREAT-PWY", "PWY-6173",
        "CHOLINE-BETAINE-ANA-PWY", "PWY-40", "PWY-46", "BSUBPOLYAMSYN-PWY",
        "UDPNACETYLGALSYN-PWY", "PWY-5270", "PWY-6133", "PWY-6358", "PWY-6365",
        "PWY-6369", "PWY-6351", "PWY-6364", "PWY-6363", "PWY-6366", "PWY-2301",
        "PWY-6554", "PWY-6362", "PWY-922", "2PHENDEG-PWY", "PWY-6181", "PWY66-414",
        "PWY6666-2", "GLUDEG-I-PWY", "PWY-6535", "PWY-3661-1", "GLUAMCAT-PWY",
        "PWY-6517", "PWY-0", "PWY-6117", "PWY66-389", "PWY66-21", "PWY66-162",
        "PWY66-161", "PWY-4261", "PWY-5453", "PWY-5386", "MGLDLCTANA-PWY", "PWY-5046",
        "PWY-5084", "PWY-6334", "HYDROXYPRODEG-PWY", "ALANINE-DEG3-PWY",
        "ASPARAGINE-DEG1-PWY", "MALATE-ASPARTATE-SHUTTLE-PWY", "BETA-ALA-DEGRADATION-I-PWY",
        "PWY-5329", "CYSTEINE-DEG-PWY", "GLUTAMINDEG-PWY", "GLYCLEAV-PWY", "PWY-5030",
        "ILEUDEG-PWY", "LEU-DEG2-PWY", "LYSINE-DEG1-PWY", "PWY-5328", "METHIONINE-DEG1-PWY",
        "PHENYLALANINE-DEG1-PWY", "PROUT-PWY", "SERDEG-PWY", "PWY66-428", "PWY66-401",
        "TRYPTOPHAN-DEGRADATION-1", "PWY-6309", "PWY-5651", "PWY-6307", "TYRFUMCAT-PWY",
        "VALDEG-PWY", "PWY-1801", "PWY-5177", "PWY-5652", "PWY0-1313", "PYRUVDEHYD-PWY",
        "PWY-5130", "PROPIONMET-PWY", "PWY-5525", "PWY-6370", "PWY-5874", "MANNCAT-PWY",
        "PWY-7180", "PWY66-422", "BGALACT-PWY", "PWY66-373", "PWY0-1182", "PWY-6576",
        "PWY-6573", "PWY-5941-1", "LIPAS-PWY", "LIPASYN-PWY", "PWY-6111", "PWY-6368",
        "PWY3DJ-11470", "PWY6666-1", "PWY-5451", "PWY-5137", "PWY66-391", "FAO-PWY",
        "PWY66-388", "PWY66-387", "PWY-6313", "PWY-6342", "PWY-6688", "PWY-6398",
        "PWY-6402", "PWY-6400", "PWY-6399", "PWY-6261", "PWY-6260", "PWY-6756",
        "PWY-6353", "PWY-7179-1", "PWY0-1296", "SALVADEHYPOX-PWY", "PWY-6608",
        "PWY-7209", "PWY-6430", "PWY-7181", "PWY-7177", "PWY0-1295", "PWY-7185",
        "PWY-4984", "PWY-5326", "PWY-5350", "PWY-4061", "PWY-7112", "PWY-6377",
        "PWY66-241", "PWY66-201", "PWY66-221", "PWY-4101", "DETOX1-PWY", "PWY-6502",
        "PWY0-1305", "PWY-4202", "PWY-6938", "PWY66-407", "PWY-5172", "PWY-5481",
        "PWY66-400", "PWY66-368", "PWY66-367", "PWY-6118", "PENTOSE-P-PWY",
        "OXIDATIVEPENT-PWY-1", "NONOXIPENT-PWY", "PWY66-398", "PWY-7437", "PWY-7434",
        "PWY-7433", "PWY66-14", "PWY66-11"]


fetch_queue = pathways = [
            'Biosynthesis',
            'Degradation',
            'Energy-Metabolism',
            ]

fetched = []
added_this_loop = None

while len(fetch_queue) > 0:
    added_this_loop = 0
    to_add = []
    for p in fetch_queue:
        print p
        pw = biocyc.get(p)
        to_add.extend(pw._super_pathways)
        to_add.extend(pw._subclasses)
        to_add.extend(pw._instances)
        
    to_add = [p for p in to_add if p not in fetched]
    fetch_queue = to_add
    fetched.extend(to_add)    
    
DEFAULT_PATHWAYS = fetched

total_n = len(DEFAULT_PATHWAYS)
for n, p in enumerate(DEFAULT_PATHWAYS):
    pw = biocyc.get(p)
    print "P", pw, pw.id, "(%d/%d)" % (n, total_n)
    for r in pw.reactions:
        print "R.", r, r.id
        for er in r.enzymatic_reactions:
            print "r..", er, er.id
            print "E...", er.enzyme, er.enzyme.id
            if er.enzyme.gene:
                print "G....", er.enzyme.gene, er.enzyme.gene.id
            for c in er.enzyme.components:
                print "C....", c, c.id
                if c.gene:
                    print "G.....", c.gene, c.gene.id
                    c.gene.pathways # Force check all are in