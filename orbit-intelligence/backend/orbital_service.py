from__future__importannotations

importjson
importmath
importos
importre
importsubprocess
importtempfile
frompathlibimportPath
fromtypingimportAny


BASE_DIR=Path(__file__).resolve().parent

FO_BINARY=BASE_DIR/"bin"/"fo"

FO_CONFIG_DIR=BASE_DIR/"findorb-data"


#Gaussiangravitationalconstant.
#AU^(3/2)/day.
GAUSSIAN_K=0.01720209895


def_require_find_orb()->None:
"""
VerifythattheFind_Orbexecutableanditsruntime
configurationareavailable.

Theseartifactsareproducedonlybythedeploy-time
scriptorbit-intelligence/render-build.sh.Theyare
intentionallyNOTcommittedtotherepositorybecause
thebinaryisplatform-specificandtheDE430ephemeris
islarge.
"""

ifnotFO_BINARY.exists():
raiseRuntimeError(
f"Find_Orbexecutablenotfoundat{FO_BINARY}.\n"
"Thedeploybuild(render-build.sh)mustcompileandinstall'fo'.\n"
"Seeorbit-intelligence/README.mdfortherequiredbuildsteps."
)

try:
size=FO_BINARY.stat().st_size
exceptOSErrorasexc:
raiseRuntimeError(
f"CannotstatFind_Orbbinaryat{FO_BINARY}:{exc}"
)fromexc

ifsize<1024:
raiseRuntimeError(
f"Find_Orbbinaryat{FO_BINARY}isonly{size}bytes.\n"
"Thisisalmostcertainlyanemptyplaceholder,notarealexecutable.\n"
"Runorbit-intelligence/render-build.sh(ortheequivalentdeploystep)\n"
"sothataproperlycompiled'fo'isinstalled."
)

ifnotos.access(FO_BINARY,os.X_OK):
raiseRuntimeError(
f"Find_Orbexistsbutisnotexecutable:{FO_BINARY}\n"
"Try:chmod+x"+str(FO_BINARY)
)

ifnotFO_CONFIG_DIR.exists():
raiseRuntimeError(
f"Find_Orbconfigurationdirectorynotfoundat{FO_CONFIG_DIR}.\n"
"render-build.shisresponsibleforcreatingthisdirectoryand\n"
"populatingitwithcospar.txt+theDE430ephemeris."
)

cospar_file=FO_CONFIG_DIR/"cospar.txt"

ifnotcospar_file.exists():
raiseRuntimeError(
"Find_Orbconfigurationisincomplete.\n"
f"Missingrequiredfile:{cospar_file}\n"
"Thisfileiscopiedbyrender-build.shfromtheFind_Orbsourcetree."
)

eph_candidates=list(FO_CONFIG_DIR.glob("*.430*"))+list(
FO_CONFIG_DIR.glob("linux_p*.430*")
)

ifnoteph_candidates:
pass


def_decimal_to_ra(
ra_deg:float,
)->tuple[int,int,float]:
"""
Convertdecimal-degreerightascensioninto
hours,minutes,seconds.
"""

total_hours=ra_deg/15.0

hours=int(total_hours)

minutes_total=(
total_hours-hours
)*60.0

minutes=int(minutes_total)

seconds=(
minutes_total-minutes
)*60.0

returnhours,minutes,seconds


def_decimal_to_dec(
dec_deg:float,
)->tuple[str,int,int,float]:
"""
Convertdecimal-degreedeclinationinto
sign,degrees,arcminutes,arcseconds.
"""

sign="+"ifdec_deg>=0else"-"

value=abs(dec_deg)

degrees=int(value)

minutes_total=(
value-degrees
)*60.0

minutes=int(minutes_total)

seconds=(
minutes_total-minutes
)*60.0

return(
sign,
degrees,
minutes,
seconds,
)


def_format_mpc_date(
time_utc:str,
)->str:
"""
ConvertanISO-ishUTCtimestamptoMPC-style:

YYYYMMDD.dddddd

Example:

2026-09-17T12:30:00Z

becomesapproximately:

20260917.520833
"""

value=(
time_utc
.strip()
.replace("Z","")
)

if"T"notinvalue:
raiseValueError(
f"InvalidUTCtimestamp:{time_utc}"
)

date_part,time_part=value.split(
"T",
1,
)

try:
year,month,day=[
int(x)
forxindate_part.split("-")
]
exceptValueErrorasexc:
raiseValueError(
f"InvalidUTCdate:{time_utc}"
)fromexc

time_part=(
time_part
.split("+")[0]
.split("-")[0]
)

parts=time_part.split(":")

iflen(parts)!=3:
raiseValueError(
f"InvalidUTCtime:{time_utc}"
)

hour=int(parts[0])
minute=int(parts[1])
second=float(parts[2])

ifnot0<=hour<=23:
raiseValueError(
f"InvalidUTChour:{time_utc}"
)

ifnot0<=minute<=59:
raiseValueError(
f"InvalidUTCminute:{time_utc}"
)

ifnot0<=second<60:
raiseValueError(
f"InvalidUTCsecond:{time_utc}"
)

day_fraction=(
hour/24.0
+minute/1440.0
+second/86400.0
)

return(
f"{year:04d}"
f"{month:02d}"
f"{day+day_fraction:09.6f}"
)


def_format_observation(
object_name:str,
time_utc:str,
ra_deg:float,
dec_deg:float,
magnitude:float|None,
)->str:
"""
FormatanobservationasanMPC-style
opticalobservationline.

Thecurrentsimulatorusessynthetic
geocentricobservatorycode500.
"""

(
ra_h,
ra_m,
ra_s,
)=_decimal_to_ra(
ra_deg
)

(
dec_sign,
dec_d,
dec_m,
dec_s,
)=_decimal_to_dec(
dec_deg
)

date_string=_format_mpc_date(
time_utc
)

ifmagnitudeisnotNone:
mag=f"{magnitude:4.1f}"
else:
mag=""

line=(
f"{object_name[:12]:<12}"
f"C"
f"{date_string:>17}"
f"{ra_h:02d}"
f"{ra_m:02d}"
f"{ra_s:05.2f}"
f"{dec_sign}"
f"{dec_d:02d}"
f"{dec_m:02d}"
f"{dec_s:04.1f}"
f""
f"{mag}"
f"500"
)

returnline[:80]


def_run_find_orb(
input_file:Path,
output_dir:Path,
)->str:
"""
Runthenon-interactiveFind_Orbexecutable.

Find_Orbrequiresitsconfigurationfiles,
includingcospar.txt.

IMPORTANT:
Find_Orb's-xalternateconfigurationdirectory
isconcatenatedinternallywithfilenames.Therefore
thedirectoryMUSTendwithapathseparator.

Example:

/app/findorb-data/

ratherthan:

/app/findorb-data
"""

ifnotFO_CONFIG_DIR.exists():
raiseRuntimeError(
"Find_Orbconfigurationdirectory"
f"doesnotexist:{FO_CONFIG_DIR}"
)

cospar_file=(
FO_CONFIG_DIR/"cospar.txt"
)

ifnotcospar_file.exists():
raiseRuntimeError(
"Find_Orbconfigurationismissing"
f"cospar.txt:{cospar_file}"
)

#Find_Orbconcatenatesthe-xdirectorydirectly
#withconfigurationfilenamessuchas"cospar.txt".
#
#Therefore:
#
#/findorb-data/+cospar.txt
#
#mustbecome:
#
#/findorb-data/cospar.txt
#
#andNOT:
#
#/findorb-datacospar.txt
config_dir_argument=str(
FO_CONFIG_DIR
)

ifnotconfig_dir_argument.endswith(
os.sep
):
config_dir_argument+=os.sep

command=[
str(FO_BINARY),
"-x",
config_dir_argument,
str(input_file),
"-v",
]

env=os.environ.copy()

#KeepFind_Orbtemporaryfilesisolated
#fromthepackagedconfigurationdirectory.
env["HOME"]=str(output_dir)

try:
process=subprocess.run(
command,
cwd=output_dir,
env=env,
capture_output=True,
text=True,
timeout=45,
)

exceptsubprocess.TimeoutExpiredasexc:
raiseRuntimeError(
"Find_Orbexceededthe"
"45-secondexecutionlimit."
)fromexc

exceptOSErrorasexc:
raiseRuntimeError(
f"CouldnotexecuteFind_Orb:{exc}"
)fromexc

combined_output=(
process.stdout
+"\n"
+process.stderr
)

ifprocess.returncode!=0:
raiseRuntimeError(
"Find_Orbfailed.\n\n"
+combined_output[-5000:]
)

returncombined_output


def_find_json_files(
directory:Path,
)->list[Path]:
"""
FindJSONproductsgeneratedbyFind_Orb.
"""

returnlist(
directory.rglob("*.json")
)


def_load_best_find_orb_json(
directory:Path,
)->dict[str,Any]:
"""
LoadthemostlikelyFind_Orborbital
solutionJSONfile.
"""

candidates=_find_json_files(
directory
)

preferred=[
path
forpathincandidates
ifpath.name.lower()
in{
"total.json",
"elements.json",
"short.json",
"elem_short.json",
}
]

candidates=(
preferred
orcandidates
)

forpathincandidates:
try:
withpath.open(
"r",
encoding="utf-8",
)asfile:
data=json.load(file)

ifisinstance(data,dict):
returndata

except(
OSError,
json.JSONDecodeError,
):
continue

raiseRuntimeError(
"Find_Orbcompletedbutnoreadable"
"JSONresultwasproduced."
)


def_recursive_find_key(
value:Any,
keys:set[str],
)->Any|None:
"""
RecursivelysearchnestedJSONdata
foroneoftherequestedkeys.
"""

ifisinstance(value,dict):

forkey,childinvalue.items():

normalized=(
str(key)
.lower()
.replace("_","")
.replace("-","")
.replace("","")
)

ifnormalizedinkeys:
returnchild

forchildinvalue.values():

result=_recursive_find_key(
child,
keys,
)

ifresultisnotNone:
returnresult

elifisinstance(value,list):

forchildinvalue:

result=_recursive_find_key(
child,
keys,
)

ifresultisnotNone:
returnresult

returnNone


def_number(
value:Any,
)->float|None:
"""
ConvertaJSONvalueintoafloat
whenpossible.
"""

ifvalueisNone:
returnNone

ifisinstance(value,bool):
returnNone

ifisinstance(
value,
(int,float),
):
returnfloat(value)

ifisinstance(value,str):

match=re.search(
r"[-+]?(?:"
r"\d+(?:\.\d*)?"
r"|"
r"\.\d+"
r")"
r"(?:[eE][-+]?\d+)?",
value,
)

ifmatch:

try:
returnfloat(
match.group(0)
)

exceptValueError:
pass

returnNone


def_extract_elements(
data:dict[str,Any],
)->dict[str,Any]:
"""
Extractcommonorbitalelementsfrom
Find_OrbJSONoutput.

Theparserintentionallysearchesrecursively
becauseFind_OrbJSONlayoutscanchange.
"""

aliases={
"a":{
"a",
"semimajoraxis",
"semimajoraxisau",
},

"e":{
"e",
"eccentricity",
},

"i":{
"i",
"inclination",
"inclinationdeg",
},

"q":{
"q",
"perihelion",
"periheliondistance",
"periheliondistanceau",
},

"om":{
"om",
"omega",
"argumentofperihelion",
"argumentofperiheliondeg",
},

"node":{
"omnode",
"longitudeofascendingnode",
"ascendingnode",
"node",
"nodeangle",
},

"M":{
"m",
"meananomaly",
"meananomalydeg",
},

"tp":{
"tp",
"timeofperihelion",
},

"epoch":{
"epoch",
"epochjd",
"jd",
},

"moid":{
"moid",
},

"h":{
"h",
"absolutemagnitude",
},
}

result:dict[str,Any]={}

foroutput_key,keysetinaliases.items():

normalized_keyset={
key.lower()
.replace("_","")
.replace("-","")
.replace("","")
forkeyinkeyset
}

raw=_recursive_find_key(
data,
normalized_keyset,
)

value=_number(raw)

ifvalueisnotNone:
result[output_key]=value

returnresult


def_derive_elements(
elements:dict[str,Any],
)->dict[str,Any]:
"""
Deriveusefulsecondaryorbitalquantities.
"""

a=elements.get("a")
e=elements.get("e")

ifaisnotNone:

ifeisnotNone:

elements.setdefault(
"perihelion_au",
a*(1.0-e),
)

elements.setdefault(
"aphelion_au",
a*(1.0+e),
)

ifa>0:

period_years=math.sqrt(
a**3
)

elements.setdefault(
"period_years",
period_years,
)

elements.setdefault(
"period_days",
period_years
*365.2568983,
)

returnelements


def_orbit_point(
a:float,
e:float,
inclination_deg:float,
node_deg:float,
arg_peri_deg:float,
true_anomaly_deg:float,
)->list[float]:
"""
ConvertaKeplerianorbitalposition
intoheliocentricCartesianAU.
"""

nu=math.radians(
true_anomaly_deg
)

inclination=math.radians(
inclination_deg
)

node=math.radians(
node_deg
)

arg_peri=math.radians(
arg_peri_deg
)

denominator=(
1.0
+e*math.cos(nu)
)

ifabs(denominator)<1e-12:
denominator=1e-12

radius=(
a
*(1.0-e*e)
/denominator
)

x_orb=(
radius
*math.cos(nu)
)

y_orb=(
radius
*math.sin(nu)
)

cos_o=math.cos(node)
sin_o=math.sin(node)

cos_i=math.cos(inclination)
sin_i=math.sin(inclination)

cos_w=math.cos(arg_peri)
sin_w=math.sin(arg_peri)

x=(
(
cos_o*cos_w
-sin_o*sin_w*cos_i
)
*x_orb
+
(
-cos_o*sin_w
-sin_o*cos_w*cos_i
)
*y_orb
)

y=(
(
sin_o*cos_w
+cos_o*sin_w*cos_i
)
*x_orb
+
(
-sin_o*sin_w
+cos_o*cos_w*cos_i
)
*y_orb
)

z=(
sin_w*sin_i*x_orb
+
cos_w*sin_i*y_orb
)

return[
x,
y,
z,
]


defgenerate_orbit_path(
elements:dict[str,Any],
samples:int=360,
)->list[list[float]]:
"""
Generateavisualorbitpathforthefrontend.
"""

a=elements.get("a")

e=elements.get(
"e",
0.0,
)

inclination=elements.get(
"i",
0.0,
)

node=elements.get(
"node",
0.0,
)

arg_peri=elements.get(
"om",
0.0,
)

ifaisNone:
return[]

ifeisNone:
e=0.0

#Currentvisualisersupports
#ellipticorbitsonly.
ifa<=0ore>=1:
return[]

points:list[list[float]]=[]

forindexinrange(samples):

anomaly=(
index
/(samples-1)
)*360.0

points.append(
_orbit_point(
a=a,
e=e,
inclination_deg=inclination,
node_deg=node,
arg_peri_deg=arg_peri,
true_anomaly_deg=anomaly,
)
)

returnpoints


defsolve_orbit(
object_name:str,
observations:list[Any],
)->dict[str,Any]:
"""
Mainorbit-determinationpipeline.

1.ValidateFind_Orbinstallation.
2.Convertfrontendobservationsinto
MPC-styleopticalobservations.
3.ExecuteBillGray'sFind_Orb.
4.LocateitsJSONorbitalsolution.
5.Extractorbitalelements.
6.Generatea3Dvisualisationpath.
"""

_require_find_orb()

iflen(observations)<3:
raiseValueError(
"Atleastthreeobservations"
"arerequired."
)

withtempfile.TemporaryDirectory(
prefix="orbit-intelligence-"
)astemp_dir:

work_dir=Path(temp_dir)

input_file=(
work_dir
/"observations.txt"
)

lines=[
_format_observation(
object_name=object_name,
time_utc=obs.time_utc,
ra_deg=obs.ra_deg,
dec_deg=obs.dec_deg,
magnitude=obs.magnitude,
)
forobsinobservations
]

input_file.write_text(
"\n".join(lines)
+"\n",
encoding="utf-8",
)

output=_run_find_orb(
input_file=input_file,
output_dir=work_dir,
)

try:

raw_json=(
_load_best_find_orb_json(
work_dir
)
)

elements=(
_extract_elements(
raw_json
)
)

exceptRuntimeError:

raiseRuntimeError(
"Find_Orbranbutthesimulator"
"couldnotlocateamachine-readable"
"orbitalsolution.\n\n"
"Find_Orboutput:\n"
+output[-6000:]
)

elements=_derive_elements(
elements
)

orbit_path=(
generate_orbit_path(
elements
)
)

return{
"engine":(
"BillGrayFind_Orb"
),

"object_name":(
object_name
),

"observation_count":(
len(observations)
),

"elements":(
elements
),

"orbit_path_au":(
orbit_path
),

"raw_output_tail":(
output[-3000:]
),
}
