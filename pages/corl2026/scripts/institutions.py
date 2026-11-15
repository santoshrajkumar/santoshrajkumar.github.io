"""Hand-checked institution table for CDC 2026 affiliations.

Each rule line: Canonical name | country (ISO2) | sector (A/I) | pattern;pattern;...
Patterns are regexes over a normalized key (lowercase ASCII, punctuation -> space,
common abbreviations expanded). Rules are applied in order; a match is cut out of
the string before later rules run, so specific names must come before general ones.
"""
import re
import unicodedata

RULES_TXT = r"""
# ---------- United States ----------
MIT Lincoln Laboratory|US|A|mit lincoln lab\w*
Massachusetts Institute of Technology|US|A|massachusetts institute of technology;mit
Georgia Institute of Technology|US|A|georgia institute of technology;georgia tech(nology)?
Purdue University|US|A|purdue
California Institute of Technology|US|A|california institute of technology;caltech
University of Michigan|US|A|university of michigan( ann arbor| at ann arbor)?;the university of michigan
UC Berkeley|US|A|(university (of )?california|uc) (at |of )?berkeley;ucb
UC San Diego|US|A|(university (of )?california|uc) (at |of )?san diego;ucsd
UCLA|US|A|(university (of )?california|uc) (at |of |a )?los angeles;ucla
UC Irvine|US|A|(university (of )?california|uc) (at |of )?irvine;uci
UC Santa Barbara|US|A|(university (of )?california|uc) (at |of )?santa barbara;ucsb
UC Santa Cruz|US|A|(university (of )?california|uc) (at |of )?santa cruz;ucsc
UC Merced|US|A|(university (of )?california|uc) (at |of )?merced
UC Riverside|US|A|(university (of )?california|uc) (at |of )?riverside
UC Davis|US|A|(university (of )?california|uc) (at |of )?davis
Lawrence Berkeley National Laboratory|US|A|lbl;lbnl;lawrence berkeley
Johns Hopkins Applied Physics Laboratory|US|A|johns? hopkins (university )?applied physics lab\w*
Johns Hopkins University|US|A|johns? hopkins
Cornell University|US|A|cornell
Northeastern University|US|A|northeastern university
Penn State University|US|A|(the )?pennsylvania state university;penn state
University of Pennsylvania|US|A|university of pennsylvania;upenn
Florida State University|US|A|florida state university;famu fsu
Florida International University|US|A|florida international
University of Central Florida|US|A|university of central florida
University of South Florida|US|A|university of south florida
University of North Florida|US|A|university of north florida
Florida Institute of Technology|US|A|florida institute of technology
University of Florida|US|A|university of florida
Vanderbilt University|US|A|vanderbilt
Stanford University|US|A|stanford
Arizona State University|US|A|arizona state
University of Arizona|US|A|university of arizona
Boston University|US|A|boston university
Boston College|US|A|boston college
University of Illinois Chicago|US|A|university of illinois chicago
University of Illinois Urbana-Champaign|US|A|university of illinois( at)? urbana( champaign)?;university of illinois urabana champaign;uiuc;university of illinois
Illinois Institute of Technology|US|A|illinois institute of technology
Washington University in St. Louis|US|A|washington university in (st|saint) louis
Washington State University|US|A|washington state university
George Washington University|US|A|(the )?george washington university
University of Washington|US|A|university of washington( seattle)?
University of Colorado Colorado Springs|US|A|university of colorado colorado springs
University of Colorado Boulder|US|A|university of colorado( at)? boulder;university of colorado
Colorado School of Mines|US|A|colorado school of mines
University of Maryland, Baltimore County|US|A|university of maryland baltimore county
University of Maryland|US|A|university of maryland( college park)?
Princeton Plasma Physics Laboratory|US|A|princeton plasma physics
Princeton University|US|A|princeton
NYU Abu Dhabi|AE|A|new york university abu dhabi( nyuad)?;nyuad
NYU Shanghai|CN|A|nyu shanghai
New York University|US|A|new york university( nyu)?;nyu( tandon school of engineering)?
UT Austin|US|A|(the )?university of texas at austin;ut austin
UT Dallas|US|A|(the )?university of texas at dallas
UT Arlington|US|A|(the )?university of texas at arlington
UT San Antonio|US|A|(the )?universi?ty of texas( at)? san antonio
UT El Paso|US|A|(the )?university of texas at el paso
UT Permian Basin|US|A|(the )?university of texas permian basin
North Carolina A&T State University|US|A|north carolina agricultural and technical
NC State University|US|A|north carolina state university( raleigh)?;nc state
UNC Charlotte|US|A|university of north carolina at charlotte
UNC Chapel Hill|US|A|university of north carolina chapel hill
University of Southern California|US|A|university of southern california
The Ohio State University|US|A|(the )?ohio state university
Ohio University|US|A|ohio university
Carnegie Mellon University|US|A|carnegie mellon
Lehigh University|US|A|lehigh
Dana-Farber Cancer Institute|US|A|dana farber
Brigham and Women's Hospital|US|A|brigham and women s hospital
Harvard University|US|A|harvard
Los Alamos National Laboratory|US|A|los alamos national\w* lab\w*;triad national security
Air Force Research Laboratory|US|A|air force research lab\w*;afrl
DEVCOM Ground Vehicle Systems Center|US|A|devcom ground vehicle
Army Research Laboratory|US|A|(us |u s |devcom )*army research lab\w*
Virginia Tech|US|A|virginia tech;virginia polytechnic institute
Virginia Commonwealth University|US|A|virginia commonwealth
University of Virginia|US|A|university of virginia
Texas A&M International University|US|A|texas a and m international
Texas A&M University|US|A|texas a and m
Texas Tech University|US|A|texas tech university;whitacre collage of engineering texas tech university
Mitsubishi Electric Research Laboratories|US|I|mitsubishi electric research lab\w*;merl
Worcester Polytechnic Institute|US|A|worcester polytechnic
Clemson University|US|A|clemson
Columbia University|US|A|columbia university
Auburn University|US|A|auburn university
Rensselaer Polytechnic Institute|US|A|rensselaer
University of New Mexico|US|A|university of new mexico
New Jersey Institute of Technology|US|A|new jersey institute of technology;njit
Iowa State University|US|A|iowa state
University of Iowa|US|A|university of iowa
Louisiana State University|US|A|louisiana state
Louisiana Tech University|US|A|louisiana tech
Rutgers University|US|A|rutgers
University of Minnesota|US|A|university of minnesota
Oak Ridge National Laboratory|US|A|oak ridge national lab\w*
University of Delaware|US|A|university of delaware
George Mason University|US|A|george mason
Dartmouth College|US|A|dartmouth
Brigham Young University|US|A|brigham young
Pacific Northwest National Laboratory|US|A|pacific northwest national lab\w*
Michigan State University|US|A|michigan state
Rice University|US|A|rice university
Naval Postgraduate School|US|A|naval postgraduate
University at Buffalo|US|A|university at buffalo
University at Albany|US|A|university at albany
Stony Brook University|US|A|stony brook
University of Vermont|US|A|university of vermont
Stevens Institute of Technology|US|A|stevens institute
University of Notre Dame|US|A|notre dame
Duke University|US|A|duke university
Kansas State University|US|A|kansas state
University of Kansas|US|A|university of kansas
San Diego State University|US|A|san diego state
Southern Methodist University|US|A|southern methodist;smu
Miami University|US|A|miami university
Rochester Institute of Technology|US|A|rochester institute of technology
Argonne National Laboratory|US|A|argonne
Syracuse University|US|A|syracuse
Marshall University|US|A|marshall university
Brown University|US|A|brown university
Toyota Research Institute|US|I|toyota research institute
Toyota Motor North America|US|I|toyota motor north america;toyota na r and d
Toyota InfoTech Labs|US|I|toyota infotech
Oakland University|US|A|oakland university
University of Alabama in Huntsville|US|A|(university|univ|university or) (of )?alabama (in|at) huntsville
University of Alabama|US|A|(the )?university of alabama
Tennessee Technological University|US|A|tennessee technological
University of Tennessee, Knoxville|US|A|(the )?university of tennessee
Lockheed Martin|US|I|lockheed martin
National Laboratory of the Rockies (NREL)|US|A|national laboratory of the rockies;national renewable energy lab\w*;nrel
Yale University|US|A|yale( university)?
Oregon Health and Science University|US|A|oregon health and science
University of Massachusetts Lowell|US|A|university of massachusetts lowell
IBM|US|I|ibm( research| corperation| corporation)?
Ericsson Research|SE|I|ericsson
Meta|US|I|meta
Google|US|I|google( deepmind| inc)?
Microsoft|US|I|microsoft
Amazon|US|I|amazon( com)?( inc)?
Case Western Reserve University|US|A|case western
University of Tulsa|US|A|(the )?university of tulsa
University of Kentucky|US|A|university of kentucky
Western Kentucky University|US|A|western kentucky
City College of New York|US|A|(the )?city college of new york
California State University, Northridge|US|A|california state university northridge
California State University, Bakersfield|US|A|california state university bakersfield
California State University, Los Angeles|US|A|california state university los angeles
California State University, Fullerton|US|A|california state university fullerton
California Polytechnic State University|US|A|california polytechnic
San José State University|US|A|san jose state
Santa Clara University|US|A|santa clara university
Mercer University|US|A|mercer university
Old Dominion University|US|A|old dominion
University of Georgia|US|A|university of georgia
Georgia Southern University|US|A|georgia southern
Sandia National Laboratories|US|A|sandia national
William & Mary|US|A|william and mary
Embry-Riddle Aeronautical University|US|A|embry riddle
University of Pittsburgh|US|A|university of pittsburgh
Augusta University|US|A|augusta university
Kennesaw State University|US|A|kennesaw
Loyola University Chicago|US|A|loyola university chicago
University of Hawaii|US|A|university of hawaii
University of South Alabama|US|A|university of south alabama
Southern Illinois University Edwardsville|US|A|southern illinois university( of)? edwardsville
University of Wyoming|US|A|university of wyoming
University of Nevada, Reno|US|A|university of nevada reno
Duquesne University|US|A|duquesne
Villanova University|US|A|villanova
University of Idaho|US|A|university of idaho
University of Connecticut|US|A|university of connecticut
Norfolk State University|US|A|norfolk state
Illinois State University|US|A|illinois state
Emory University|US|A|emory
General Atomics|US|I|general atomics
South Dakota School of Mines and Technology|US|A|south dakota school of mines
JPMorgan Chase|US|I|jp morgan
University of Chicago|US|A|(the )?university of chicago
Missouri University of Science and Technology|US|A|missouri university of science and technology
Furman University|US|A|furman
Yeshiva University|US|A|yeshiva
Wayne State University|US|A|wayne state
The College of New Jersey|US|A|(the )?college of new jersey
United States Military Academy|US|A|united states military academy
NASA Jet Propulsion Laboratory|US|A|nasa jpl;jet propulsion lab\w*
NASA|US|A|nasa
Zoox|US|I|zoox
RTX Technology Research Center|US|I|rtx technology research center( rtrc)?;united technologies research center
The Aerospace Corporation|US|A|(the )?aerospace corporation
Flatiron Institute|US|A|flatiron institute;simons foundation
Fujitsu|JP|I|fujitsu( research of america)?
Hewlett Packard Enterprise|US|I|hpe
American Automatic Control Council|US|A|american automatic control council
USDA Agricultural Research Service|US|A|usda( ars)?
National Institute of Mental Health|US|A|national institute of mental health
Sixth Sense Autonomy|US|I|sixth sense autonomy
Torch Technologies|US|I|torch technologies
Beta Technologies|US|I|beta technologies
Fervo Energy|US|I|fervo energy
Delsys|US|I|delsys
Newton Energy Group|US|I|newton energy group
SimpleRose|US|I|simplerose
Applied Dynamics International|US|I|applied dynamics international
Senseau Technologies|US|I|senseau
Onyx Robotics|US|I|onyx robotics
JuliaHub|US|I|juliahub
Ganzfried Research|US|I|ganzfried research
OrbitLink Consulting|US|I|orbitlink
Cigus GmbH|DE|I|cigus
Topos Institute|US|A|topos institute
University of Wisconsin–Madison|US|A|university of wisconsin( madison)?
Cleveland State University|US|A|cleveland state
University of South Carolina|US|A|university of south carolina
Oklahoma State University|US|A|oklahoma state
James Madison University|US|A|james madison
Feniix Group|US|I|feniix
Atmanity|US|I|atmanity
# ---------- Europe ----------
University of Sannio|IT|A|universita del sannio
ONERA|FR|A|onera
Izmir Katip Celebi University|TR|A|izmir katip celebi
Campus Bio-Medico University of Rome|IT|A|university campus bio medico
University of Florence|IT|A|universita degli studi di firenze
KTH Royal Institute of Technology|SE|A|kth( royal institute of technology| stockholm)?;royal ins\w* of technology
Scania|SE|I|scania
Eindhoven University of Technology|NL|A|eindhoven university of technology;technische universiteit eindhoven;tu eindhoven
EPFL|CH|A|epfl;ecole polytechnique federale de lausanne
ETH Zurich|CH|A|eth zurich;ethz;eth;swiss federal institute of technology( eth)? zurich
Politecnico di Torino|IT|A|politecnico di torino
Politecnico di Milano|IT|A|politecnico di milano
Politecnico di Bari|IT|A|politecnico di bari;polytechnic (university )?of bari
University of Oxford|GB|A|university of oxford
Imperial College London|GB|A|imperial college( london)?
University of Groningen|NL|A|university of groningen
University of Cyprus|CY|A|university of cyprus;kios center of excellence
Technical University of Munich|DE|A|technical university (of )?munich;technische universitat munchen;tachnical university of munich
Ludwig Maximilian University of Munich|DE|A|ludwig maximilian university of munich;lmu munich
University of the Bundeswehr Munich|DE|A|university of the bundeswehr munich
Munich University of Applied Sciences|DE|A|munich university of applied sciences
Lund University|SE|A|lund university
Uppsala University|SE|A|uppsala
University of Manchester|GB|A|(the )?university of manchester
University of Cagliari|IT|A|university of cagliari
Inria|FR|A|inria\w*( lille| sophia antipolis| bordeaux| nancy)?;national institute for research in digital science and technology( inria)?
RWTH Aachen University|DE|A|rwth aachen
University of Bergamo|IT|A|university of bergamo;universita degli studi di bergamo
TU Dortmund University|DE|A|tu dortmund( university)?
Leibniz University Hannover|DE|A|leibniz university hannover
University of L'Aquila|IT|A|university of l ?aquila
IMT School for Advanced Studies Lucca|IT|A|imt (school|institute) for advanced studies( lucca)?;imt lucca
UCLouvain|BE|A|uclouvain;universite catholique de louvain;university of louvain
KU Leuven|BE|A|ku leuven
University of Stuttgart|DE|A|university (of )?stuttgart
University of Bologna|IT|A|university of bologna( italy)?;universita di bologna
Chalmers University of Technology|SE|A|chalmers( university( of technology)?)?
Hamburg University of Technology|DE|A|hamburg university of technology
NTNU|NO|A|norwegian university of science and technology( ntnu)?;ntnu
University of Cambridge|GB|A|university of cambridge
Technische Universität Braunschweig|DE|A|technische universitat braunschweig;technical university of braunschweig
Johannes Kepler University Linz|AT|A|johannes kepler universit\w*( linz)?
Karlsruhe Institute of Technology|DE|A|karlsruher? institute of technology( kit)?;kit
Scuola Superiore Meridionale|IT|A|scuola superiore meridionale
Scuola Superiore Sant'Anna|IT|A|scuola superiore sant anna
Delft University of Technology|NL|A|delft university of technology;tu delft
University of Rome Tor Vergata|IT|A|(universita degli studi di roma |university of rome |universita di roma |university rome |universita di roma )?tor vergata( university)?;universita degli studi di roma tor vergata
Sapienza University of Rome|IT|A|sapienza( university of rome| universita di roma)?;universita degli studi di roma la sapienza
Roma Tre University|IT|A|roma tre( university)?;universita roma 3
Technische Universität Ilmenau|DE|A|technische universitat ilmenau;tu ilmenau
Bilkent University|TR|A|bilkent
Technion – Israel Institute of Technology|IL|A|technion( israel institute of technology)?
Linköping University|SE|A|linkoping university( liu)?
National Research Council of Italy (CNR)|IT|A|cnr (ieiit|iasi);iasi cnr;national research council of italy( cnr iasi)?;consiglio nazionale delle ricerche( cnr)?
CentraleSupélec|FR|A|centralesupelec( l2s)?;l2s centralesupelec;laboratory of signals and systems
Université Paris-Saclay|FR|A|(universite |university )?(of )?paris saclay( evry| ueve)?;universite d evry
Federal University of Minas Gerais|BR|A|federal university of minas gerais;universidade federal de minas gerais
CEFET-MG|BR|A|cefet mg
Ege University|TR|A|ege university
University of Sheffield|GB|A|university of sheffield
Graz University of Technology|AT|A|graz university of technology
University of Naples Federico II|IT|A|(university of naples |universita di napoli )?federico ii( university of naples)?
University of Porto|PT|A|university of porto
Télécom SudParis|FR|A|telecom sudparis
ENSTA Paris|FR|A|ensta( paris| paristech)?
École Polytechnique|FR|A|ecole polytechnique( cnrs)?;cmap
University of Nottingham|GB|A|university of nottingham
University of Seville|ES|A|university of seville;universidad de sevilla
Technical University of Denmark|DK|A|technical university of denmark;denmark technical university
Université de Lorraine|FR|A|universite de lorraine;university of lorraine;cran
Technical University of Crete|GR|A|technical university of crete
Tel Aviv University|IL|A|tel aviv university;tel aviv university
Brandenburg University of Technology|DE|A|(the )?brandenburg university of technology( cottbus senftenberg)?
Aalto University|FI|A|aalto university
Saarland University|DE|A|saarland university
University of Klagenfurt|AT|A|university of klagenfurt;klagenfurt university;universitat klagenfurt
University of Southampton|GB|A|university of southampton
University of Zaragoza|ES|A|universidad de zaragoza
University of Bayreuth|DE|A|university of bayreuth
Brno University of Technology|CZ|A|brno university of technology
Budapest University of Technology and Economics|HU|A|budapest university of technology
University of Padova|IT|A|university of (padova|padua)( padua)?;universita( degli studi)? di padova
Technical University of Darmstadt|DE|A|technical university (of )?darmstadt;technische universitat darmstadt;tu darmstadt
University of Patras|GR|A|university of patras
Ulm University|DE|A|ulm university;universitat ulm
Max Planck Institute for Dynamics of Complex Technical Systems|DE|A|max planck institute for dynamics of complex\w*( technical\w*)?( systems)?
Max Planck Institute for Software Systems|DE|A|max planck institute for software systems
Robert Bosch GmbH|DE|I|robert bosch
University of Trieste|IT|A|university of trieste;universita degli studi di trieste
University of Milano-Bicocca|IT|A|(university of |universita di )milano bicocca
University of Würzburg|DE|A|university of wurzburg
INSA Lyon|FR|A|insa lyon( laboratoire ampere)?
University of Bern|CH|A|university of bern
TU Dresden|DE|A|technische universitat dresden;technical university of dresden
University of Kassel|DE|A|university of kassel
Marche Polytechnic University|IT|A|universita politecnica delle marche
University of Birmingham|GB|A|university of birmingham
University of Liverpool|GB|A|(the )?university of liverpool
Comenius University|SK|A|comenius
Bialystok University of Technology|PL|A|bialystok
University of Udine|IT|A|(university|universita) (degli studi )?(of |di )?udine
University of Calabria|IT|A|university of calabria;universita (degli studi )?della calabria
École Centrale de Nantes|FR|A|(ecole )?centrale (de )?nantes( ls2n)?
École Centrale de Lille|FR|A|ecole centrale de lille
Safran Tech|FR|I|safran tech
University of Applied Sciences Kempten|DE|A|university of applied sciences kempten
Université Polytechnique Hauts-de-France|FR|A|universite polytechnique hauts de france;university polytechnic hauts de france;insa hauts de france;lamih;universite de valenciennes
Newcastle University|GB|A|newcastle university
University of Brescia|IT|A|university of brescia
University of Exeter|GB|A|university of exeter
University of East London|GB|A|university of east london
University of Wuppertal|DE|A|university of wuppertal
VITO / EnergyVille|BE|A|vito( energyville)?;flemish institute for technological research
IDSIA (USI-SUPSI)|CH|A|idsia( usi supsi)?;usi supsi;supsi;scuola universitaria pro\w* della svizzera italiana;university of applied sciences and arts of southern switzerland( supsi)?
Otto von Guericke University Magdeburg|DE|A|otto von guericke
Bretagne INP / UBO|FR|A|bretagne inp ubo( irdl)?
Ruhr University Bochum|DE|A|ruhr universitat bochum
Forschungszentrum Jülich|DE|A|forschungszentrum julich;fzj
Fraunhofer|DE|A|fraunhofer\w*( ieg)?
Waseda University|JP|A|waseda
Austrian Institute of Technology|AT|A|austrian institute of technology
Helmholtz-Zentrum Berlin|DE|A|helmholtz zentrum berlin
University of Oslo|NO|A|university of oslo
STFC|GB|A|stfc( hartree centre)?
University of Trento|IT|A|university of trento
German Aerospace Center (DLR)|DE|A|german aerospace center( dlr)?;dlr
Grenoble INP|FR|A|grenoble inp;grenoble institute of technology( grenoble inp)?
Université Grenoble Alpes|FR|A|(universite |university |univ )?grenoble alpes;gipsa\w*( lab)?
CNRS|FR|A|cnrs( lagepp| lamih)?;laas
University of Siena|IT|A|universita di siena
Stockholm University|SE|A|stockholm university
University of Gabès|TN|A|(university of )?gabes( university)?
Gebze Technical University|TR|A|gebze
Loughborough University|GB|A|loughborough
Middle East Technical University|TR|A|middle east technical
Instituto Superior Técnico, University of Lisbon|PT|A|instituto superior tecnico;university of lisbon
Gdansk University of Technology|PL|A|gdansk
Universitas Mercatorum|IT|A|(universita |university )mercatorum
Comillas Pontifical University|ES|A|comillas
University of Pavia|IT|A|university of pavia
Luleå University of Technology|SE|A|lulea( university of technology| tekniska universitet)
Université Claude Bernard Lyon 1|FR|A|universite (claude bernard )?lyon 1;universite de lyon
Free University of Bolzano|IT|A|free university of bolzano
Aalborg University|DK|A|aalborg university
Technical University of Cluj-Napoca|RO|A|cluj napoca
Huawei|CN|I|huawei( research center switzerland)?
University of Salerno|IT|A|university of salerno
University College London|GB|A|university college london
Uninettuno University|IT|A|uninettuno
UniDistance Suisse|CH|A|unidistance suisse
City St George's, University of London|GB|A|city st george s university of london
Renault (Ampere)|FR|I|renault;ampere;tcr
FHNW|CH|A|university of applied science northwestern switzerland( fhnw)?
INRAE|FR|A|inrae
University of Montpellier|FR|A|university montpellier
Tallinn University of Technology|EE|A|tallinn
HUN-REN SZTAKI|HU|A|(institute for computer science and control )?hun ren sztaki( hungarian research network)?
University of Rennes|FR|A|university of rennes
Maastricht University|NL|A|maastricht
University of Oulu|FI|A|university of oulu
Vrije Universiteit Amsterdam|NL|A|vrije universiteit
University Le Havre|FR|A|university le havre
Technische Universität Chemnitz|DE|A|technische universitat chemnitz
RPTU Kaiserslautern-Landau|DE|A|rptu( university kaiserslautern landau)?;university of kaiserslautern landau
National University of Science and Technology POLITEHNICA Bucharest|RO|A|universitatea nationala de stiinta si tehnologie politehnica bucuresti;university politehnica of bucharest;unstpb
University of Bucharest|RO|A|university of bucharest
Inspire AG|CH|I|inspire ag
University of St Andrews|GB|A|university of st andrews
University of Turin|IT|A|university of turin
Collegio Carlo Alberto|IT|A|collegio carlo alberto
IE University|ES|A|ie university
Spanish National Research Council (CSIC)|ES|A|spanish national research council;high council for scientific research csic
ABB|SE|I|abb( robotics sweden)?
TU Berlin|DE|A|tu berlin
Hebrew University of Jerusalem|IL|A|hebrew university
University of Passau|DE|A|university of passau
University of Thessaly|GR|A|university of thessaly
Athena Research Center|GR|A|athena rc
University of Twente|NL|A|university of twente
University College Dublin|IE|A|university college dublin
Istanbul Technical University|TR|A|istanbul technical
Bogazici University|TR|A|bogazici
Durham University|GB|A|durham university
Middlesex University|GB|A|middlesex
Italian Institute of Artificial Intelligence for Industry|IT|A|(the )?italian institute of artificial intelligence for industry
University of Bristol|GB|A|university of bristol
Mines Paris – PSL|FR|A|mines paris psl
Sorbonne University|FR|A|sorbonne universit\w*;laboratoire jacques louis lions
Cnam|FR|A|cnam
EURECOM|FR|A|eurecom
ENSEA|FR|A|ensea
DNV|NO|I|dnv
Eelume|NO|I|eelume
Thales|FR|I|thales( group)?
Marchesini Group|IT|I|marchesini group
University of Hohenheim|DE|A|university of hohenheim
UMIT TIROL|AT|A|umit tirol
University of Duisburg-Essen|DE|A|university of duisburg essen
ENIB Brest|FR|A|ecole nationale d ingenieurs de brest
OTH Regensburg|DE|A|ostbayerische technische hochschule regensburg;oth regensburg
University of Perugia|IT|A|university of perugia;universita degli studi di perugia
LUISS Guido Carli|IT|A|luiss
University of Murcia|ES|A|university of murcia;universidad de murcia
Technical University of Cartagena|ES|A|technical university of cartagena
Eötvös Loránd University|HU|A|eotvos lorand
Université Marie et Louis Pasteur|FR|A|universite marie et louis pasteur( supmicrotech)?
Orange Research|FR|I|orange research
Avignon Université|FR|A|avignon universite
Innopolis University|RU|A|innopolis
Skoltech|RU|A|skoltech
Central University (Moscow)|RU|A|central university
Sirius University|RU|A|sirius university
Matrosov Institute for System Dynamics and Control Theory|RU|A|matrosov institute
Institute for Problems in Mechanics, RAS|RU|A|institute for problems in mechanics
Arzamas Polytechnic Institute (NNSTU)|RU|A|arzamas polytechnic institute
Champalimaud Research|PT|A|champalimaud
Taras Shevchenko National University of Kyiv|UA|A|taras shevchenko
King's College London|GB|A|king s college london
Coventry University Kazakhstan|KZ|A|coventry university kazakhstan
LUT University|FI|A|lappeenranta
Université de Sherbrooke|CA|A|universite de sherbrooke
University of Luxembourg|LU|A|university of luxembourg
Czech Technical University in Prague|CZ|A|czech technical university
Slovak University of Technology in Bratislava|SK|A|slovak university of technology
National Technical University of Athens|GR|A|national technical university of athens
University of Applied Sciences Hainan-Bielefeld|CN|A|hainan bielefeld
UK Atomic Energy Authority|GB|A|(united kingdom|uk) atomic energy authority
National Institute of Materials Physics|RO|A|national institu\w* of materials physics
Université Côte d'Azur (I3S)|FR|A|i3s( cnrs)?( uca)?;laboratoire i3s uca
Université de Lille|FR|A|university of lille;inria univ lille
Väderstad AB|SE|I|vaderstad
AMIAD|FR|A|amiad
Strouwen Statistics|BE|I|strouwen statistics
De Vinci Research Center|FR|A|de vinci research center
COVE|GB|A|cove
# ---------- Asia / Middle East ----------
Shanghai Jiao Tong University|CN|A|shanghai jiao ?tong university
Seoul National University of Science and Technology|KR|A|seoul national university of science and technology
Seoul National University|KR|A|seoul national university
Southeast University|CN|A|southeast university
Tsinghua University|CN|A|tsinghua( university)?
Zhejiang Normal University|CN|A|zhejiang normal university
Zhejiang University|CN|A|zhejiang university( china)?;zhejiang univ\w*;institute of cyber systems and control
Tongji University|CN|A|tongji
University of Tokyo|JP|A|(the )?university of tokyo
Nanyang Technological University|SG|A|nanyang tech\w* university( singapore)?;ntu singapore;nanyang technology university
KAIST|KR|A|kaist( korea advanced institute of science and technology)?;korea advanced institute of science and technology
Southern University of Science and Technology|CN|A|southern university of science and technology
The Chinese University of Hong Kong, Shenzhen|CN|A|(the )?chinese universi\w* of hong kong shenzhen;cuhk shenzhen
Shenzhen Research Institute of Big Data|CN|A|shenzhen research institute of big data( sribd)?
The Chinese University of Hong Kong|HK|A|(the )?chinese university of hong kong
Kyoto University|JP|A|kyoto university
Institute of Science Tokyo|JP|A|institute of science tokyo;tokyo institute of technology
Peking University|CN|A|peking university
Beihang University|CN|A|beihang
Beijing Institute of Technology|CN|A|beijing institute (of|fo) technology
Hiroshima University|JP|A|hiroshima university
HKUST (Guangzhou)|CN|A|(the )?hong kong university of sciences? and techn\w* guangzhou;hkust gz
HKUST|HK|A|(the )?hong kong university of science and technology
Nanjing University of Science and Technology|CN|A|nanjing university of science and technology
Nanjing University of Aeronautics and Astronautics|CN|A|nanjing university of aeronautics
Nanjing University|CN|A|nanjing university
Huazhong University of Science and Technology|CN|A|huazhong university of science and technology
City University of Hong Kong|HK|A|city university of hong ?kong
KAUST|SA|A|kaust;king abdullah university of science and technology
Osaka Metropolitan University|JP|A|osaka metropolitan
The University of Osaka|JP|A|(the )?university of osaka;osaka university
National University of Defense Technology|CN|A|national university of defense technology
National University of Singapore|SG|A|national university of singapore
Indian Institute of Technology Kanpur|IN|A|(indian institute of technology|iit) kanpur
Indian Institute of Technology Bombay|IN|A|(indian institute of technolog\w*|iit) bombay
Indian Institute of Technology Mandi|IN|A|(indian institute of technology|iit) mandi
Indian Institute of Technology Madras|IN|A|(indian institut\w* of technology|iit) madras
Indian Institute of Technology Kharagpur|IN|A|(indian institute of technology|iit) kharagpur
Indian Institute of Technology Delhi|IN|A|(indian institute of technology|iit) delhi
Indian Institute of Technology Guwahati|IN|A|(indian institute of technology|iit) guwahati
Indian Institute of Technology Tirupati|IN|A|(indian institute of technology|iit) tirupati
Indian Institute of Technology Dharwad|IN|A|(indian institute of technology|iit) dharwad
Indian Institute of Technology (BHU) Varanasi|IN|A|iit (bhu )?(varanasi|bhu)
Indian Institute of Science Education and Research Bhopal|IN|A|indian institute of science education and research bhopal
Indian Institute of Space Science and Technology|IN|A|indian institute of space science
Indian Institute of Science|IN|A|indian institute of science( bengaluru| bangalore)?
IIIT Delhi|IN|A|indraprastha institute of information technology
National Sun Yat-sen University|TW|A|national sun yat sen
Sun Yat-sen University|CN|A|sun yat sen university
POSTECH|KR|A|postech( pohang university of science and technology)?;pohang university of science and technology( postech)?
Inha University|KR|A|inha university
Kyushu Institute of Technology|JP|A|kyushu institute of technology
Kyushu University|JP|A|kyushu university
Xiamen University|CN|A|xiamen university
University of Shanghai for Science and Technology|CN|A|university of shanghai for science (and|and) technology
Shanghai University|CN|A|shanghai university
DGIST|KR|A|dgist;daegu gyeo\w* institu\w* of science and technology( dgist)?
University of Electronic Science and Technology of China|CN|A|university of electronic science and technology of china
University of Chinese Academy of Sciences|CN|A|university of chinese aca\w* of sciences;university of chinese academy
Chinese Academy of Sciences|CN|A|chinese aca\w* of sciences;academy of mathematics and systems science
Keio University|JP|A|keio
Northwestern Polytechnical University|CN|A|northwestern polytechnical
Meiji University|JP|A|meiji
University of Macau|MO|A|university of macau
Macau University of Science and Technology|MO|A|macau university of science and technology
The University of Electro-Communications|JP|A|(the )?university of electro communications
Dalian University of Technology|CN|A|dalian university of technology
Nankai University|CN|A|nankai
Hokkaido University|JP|A|hokkaido university
Ritsumeikan University|JP|A|ritsumeikan
Chongqing Normal University|CN|A|chongqing normal
Chongqing University|CN|A|chongqing university
ShanghaiTech University|CN|A|shanghaitech
Harbin Institute of Technology|CN|A|harbin institute of technology( shenzhen)?;state key laboratory of robotics and systems hit
Hainan University|CN|A|hainan university
Beijing University of Technology|CN|A|beijing university of technology
Hanwha Systems|KR|I|hanwha
Ho Chi Minh City University of Technology|VN|A|(hcmut )?ho chi minh city university of technology
Xi'an Jiaotong-Liverpool University|CN|A|xi an jiaotong liverpool
Xi'an Jiaotong University|CN|A|xi an jiaotong university
Qatar University|QA|A|qatar university
Zhengzhou University|CN|A|zhengzhou university
Korea Institute of Robotics and Technology Convergence|KR|A|korea institute of robotics
BITS Pilani|IN|A|bits pilani
Hangzhou Dianzi University|CN|A|hangzhou dianzi
South China University of Technology|CN|A|south china university of technology
Tokyo Metropolitan University|JP|A|tokyo metropolitan
Korea Aerospace Research Institute|KR|A|korea aerospace research institute( kari)?
GIST|KR|A|gwangju institute of science and technology( gist)?
Kochi University of Technology|JP|A|kochi university of technology
Kochi University|JP|A|kochi university
Fudan University|CN|A|fudan
Qingdao University of Science and Technology|CN|A|qingdao university of science
Central South University|CN|A|central south university
Suzhou University of Science and Technology|CN|A|suzhou university of science
Jiangsu Normal University|CN|A|jiangsu normal
Khalifa University|AE|A|khalifa university( of science and technology)?
Lebanese American University|LB|A|lebanese american
American University of Sharjah|AE|A|american university of sharjah
Tata Consultancy Services|IN|I|tata consultancy
Samsung|KR|I|samsung( research)?
Hongik University|KR|A|hongik
UNIST|KR|A|unist;ulsan national institute of science and technology
ETRI|KR|A|etri
Tokyo University of Agriculture and Technology|JP|A|tokyo university of agriculture and technology
Changshu Institute of Technology|CN|A|changs\w* institute of technology
Nagoya University|JP|A|nagoya university
Singapore University of Technology and Design|SG|A|singapore university of technology and design
Agency for Science, Technology and Research (A*STAR)|SG|A|agency for science technology and research
Sri Sathya Sai Institute of Higher Learning|IN|A|sri sathya sai
SRM University AP|IN|A|srm university
PowerChina Huadong Engineering|CN|I|powerchina
AVIC Chengdu Aircraft Design|CN|I|avic
Pusan National University|KR|A|pusan national
Sookmyung Women's University|KR|A|sookmyung
Shenzhen University of Advanced Technology|CN|A|shenzhen university of advanced technology
Shenzhen University of Information Technology|CN|A|shenzhen university of information technology
Sardar Patel Institute of Technology|IN|A|sardar patel institute
National Institute of Technology Warangal|IN|A|national institute of technology warangal
Motilal Nehru National Institute of Technology|IN|A|motilal nehru
Central Research Institute of Electric Power Industry|JP|A|central research institute of electric power
Air University|PK|A|air university
University of Peradeniya|LK|A|peradeniya
Vietnam National University HCMC|VN|A|vietnam national university
Chung-Ang University|KR|A|chung ang
Guizhou University|CN|A|guizhou university
East China University of Science and Technology|CN|A|east china university of science and technology
Mohammed VI Polytechnic University|MA|A|um6p( university mohammed 6 polytechnic)?;(university )?mohammed vi polytechnic( university)?
Mohammed V University in Rabat|MA|A|university mohammed v rabat
International University of Rabat|MA|A|international university of rabat
Sidi Mohamed Ben Abdellah University|MA|A|sidi mohamed ben abdellah
China University of Mining and Technology|CN|A|china university of mining
China University of Petroleum|CN|A|china university of petroleum
Nanzan University|JP|A|nanzan
Gunma University|JP|A|gunma
Polytechnic University of Japan|JP|A|(the )?polytechnic university of japan
National Institute of Informatics|JP|A|national institute of informatics
NICT|JP|A|national institute of information and communications technology
Yamaguchi University|JP|A|yamaguchi university
Kindai University|JP|A|kindai
University of Tsukuba|JP|A|university of tsukuba
Anhui University|CN|A|anhui university
Southwest University of Science and Technology|CN|A|southwest university of science
University of Malakand|PK|A|malakand
National Tsing Hua University|TW|A|national tsing hua
North China University of Water Resources and Electric Power|CN|A|north china university of water
Sultan Qaboos University|OM|A|sultan qaboos
TCG CREST|IN|A|tcg crest
University of Science and Technology of China|CN|A|university of science and technology of china
IIEST Shibpur|IN|A|indian institute of engineering science and technology
Minia University|EG|A|minia
Nagaoka University of Technology|JP|A|nagaoka university of technology
Korea Institute of Fusion Energy|KR|A|korea institute of fusion energy
Mitsubishi Electric Corporation|JP|I|(advanced technology r and d center )?mitsubishi electric corporation
Tokyo Gas|JP|I|tokyo gas
Seiko Solutions|JP|I|seiko solutions
TMEIC|JP|I|tmeic
Toyota|JP|I|toyota
University of Hong Kong|HK|A|(the )?university of hong ?kong;hku shenzhen institute
Mouloud Mammeri University of Tizi-Ouzou|DZ|A|mouloud mammeri
University of Monastir|TN|A|university of monastir
Sichuan University|CN|A|sichuan university;scihuan university
National Academy of Sciences of Armenia|AM|A|institute of mathematics (nas|of armenia|nas ra)\w*( of armenia)?
American University of Armenia|AM|A|american university of armenia
Center for Scientific Innovation and Education (Armenia)|AM|A|(digrea lab )?center (of|for) scientific innovation and education;digrea lab
# ---------- Oceania / Americas (non-US) ----------
University of Melbourne|AU|A|(the )?university of melbourne
University of Sydney|AU|A|(the )?university of sydney
Australian National University|AU|A|(the )?australian national university
University of New South Wales|AU|A|(the )?university of new south wales;unsw
Monash University|AU|A|monash
Western Sydney University|AU|A|western sydney
Adelaide University|AU|A|(the )?university of adelaide;adelaide university
Macquarie University|AU|A|macquarie
University of Technology Sydney|AU|A|university of technology sydney
Defence Science and Technology Group|AU|A|defence science and technology( group)?;dst group
Queen's University|CA|A|queen s university( kingston)?;queens university
University of Waterloo|CA|A|university of waterloo
Concordia University|CA|A|concordia university
University of Toronto|CA|A|university of toronto
University of British Columbia|CA|A|university of british columbia
McGill University|CA|A|mcgill
University of Alberta|CA|A|university of alberta
Polytechnique Montréal|CA|A|polytechnique montreal;ecole poly\w* de montreal
University of Montreal|CA|A|university of montreal
GERAD|CA|A|gerad
Mila|CA|A|mila
University of Guelph|CA|A|university of guelph
Lakehead University|CA|A|lakehead
Carleton University|CA|A|carleton
York University|CA|A|york university
University of New Brunswick|CA|A|university of new brunswick
University of Victoria|CA|A|university of victoria
Université du Québec en Outaouais|CA|A|university of quebec in outaouais
Université du Québec à Trois-Rivières|CA|A|uqtr
Timadie|CA|I|timadie
Royal Military College of Canada|CA|A|royal military college
RBC Borealis|CA|I|rbc borealis;royal bank of canada
École de technologie supérieure|CA|A|ecole de technologie superieure
Simon Fraser University|CA|A|simon fraser
Federal University of Rio de Janeiro|BR|A|universidadel? federal do rio de janeiro;federal university of rio de janeiro
State University of Rio de Janeiro|BR|A|state university of rio de janeiro
Federal University of Campina Grande|BR|A|universidade federal de campina grande
Federal University of Paraíba|BR|A|universidade federal da paraiba
Federal University of Santa Catarina|BR|A|universidade federal de santa catarina
University of São Paulo|BR|A|(the )?university of sao paulo;escola politecnica da universidade de sao paulo
Aeronautics Institute of Technology (ITA)|BR|A|aeronautics institute of technology
University of Chile|CL|A|university of chile
University of Santiago, Chile|CL|A|universidad de santiago de chile
Pontifical Catholic University of Chile|CL|A|pontificia universidad catolica de chile
Universidad Técnica Federico Santa María|CL|A|universidad tecnica federico santa maria
Universidad Adolfo Ibáñez|CL|A|universidad adolfo ibanez
University of Guadalajara|MX|A|university of guadalajara( udg)?
CINVESTAV|MX|A|cinvestav( ipn)?;center of research and advanced studies
Instituto Politécnico Nacional|MX|A|instituto politecnico nacional;esime upt ipn
Tecnológico Nacional de México / IT La Laguna|MX|A|tecnologico nacional de mexico( i t la laguna)?;instituto tecnologico de la laguna
ITAM|MX|A|itam
UNAM|MX|A|national autonomous university of mexico;universidad nacional autonoma de mexico
CONICET|AR|A|conicet( intec| universidad nacional del litoral)?;cifasis
National University of Rosario|AR|A|national university of rosario
National University of Trujillo|PE|A|national university of trujillo
Universidad de los Andes|CO|A|universidad de los andes
Universidad Nacional de Colombia|CO|A|universidad nacional de colombia
"""

WORD_FIX = {
    'univ': 'university', 'universty': 'university', 'univeristy': 'university', 'unviersity': 'university',
    'univerisity': 'university', 'unversity': 'university', 'universtiy': 'university', 'unviersty': 'university',
    'universitaet': 'universitat', 'universita': 'universita', 'inst': 'institute', 'institue': 'institute',
    'insitute': 'institute', 'techonology': 'technology', 'sci': 'science',
    'acedemy': 'academy', 'polytechnich': 'polytechnic', 'institution': 'institution', 'nationall': 'national',
    'labs': 'lab', 'clemson': 'clemson', 'tachnical': 'technical', 'unviersity': 'university', 'universtiy': 'university',
}


def norm(s):
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace('&', ' and ').replace('ł', 'l').replace('ø', 'o')
    s = re.sub(r'[^a-z0-9]+', ' ', s).strip()
    toks = [WORD_FIX.get(t, t) for t in s.split()]
    s = ' '.join(toks)
    s = re.sub(r'\b(of) of\b', r'\1', s)
    s = re.sub(r'\b(of|and) tech$', r'\1 technology', s)
    s = re.sub(r'\buniversity di\b', 'universita di', s)
    # "georgia institute of technology" written "georgia institute of tech" etc. already expanded
    s = s.replace('technology university', 'technological university') if 'nanyang' in s else s
    return s


RULES = []
for line in RULES_TXT.strip().splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    name, cc, sec, pats = line.split('|', 3)
    rx = re.compile(r'(?<![a-z0-9])(?:' + '|'.join(p.strip() for p in pats.split(';')) + r')(?![a-z0-9])')
    RULES.append((name, cc, sec, rx))

COMPANY = re.compile(r'\b(inc|corp|corporation|llc|ltd|gmbh|s p a|spa|ag|as|co|company|technologies|labs? inc)\b')


def clean_fallback(raw):
    s = re.sub(r'\s+', ' ', raw).strip().strip(',;/ ')
    s = re.sub(r'^(the|department of [^,]+,|school of [^,]+,|faculty of [^,]+,|college of [^,]+,)\s*', '', s, flags=re.I).strip()
    return s


def resolve(raw):
    """Return list of (canonical, country, sector) for one affiliation string."""
    key = ' ' + norm(raw) + ' '
    hits = []
    for name, cc, sec, rx in RULES:
        m = rx.search(key)
        while m:
            if name not in [h[0] for h in hits]:
                hits.append((name, cc, sec, m.start()))
            key = key[:m.start()] + ' # ' + key[m.end():]
            m = rx.search(key)
    if hits:
        hits.sort(key=lambda h: h[3])
        return [h[:3] for h in hits]
    junk = norm(raw)
    if not junk or junk in ('student', 'independent', 'independent researcher', 'assistant professor', 'research assitant'):
        return []
    name = clean_fallback(raw)
    sec = 'I' if COMPANY.search(norm(raw)) else 'A'
    return [(name, '', sec)]
