")r run-ios)(odroid tive run-annact-x rea np3.  print("")
  llm instanpint("2.  pr)
   obile"er_mrads_tutilu("1. cd na   printp:")
 o run the apt("T)
    prindir}"ator.app_tory: {generpp direc  print(f"Ally")
  fuuccessnerated sgeon e applicatie mobil"React Nativ    print(
    
ture()_strucate_apperator.gener
    genconfig)tor(ppGeneraNativeActea= Rrator  geneive app
    Nate React  # Generat )
    
  0"
   1.0.ersion=",
        vder.mobile"nautilustra"com.dle_id=bun      ,
  er"tilus Trad_name="Nau       apponfig(
 leAppCfig = Mobi   conuration
 nfige app coCreate mobil  
    # )
  ing.INFOoggvel=lg(leonfi.basicCng    loggiin__":
_ == "__ma
if __name_age# Example us

''
();
'erviceClassificationS= new Notce ervionSicati const Notif
export }
}
s();
 ionalNotificatAllLocation.cancelotific PushN   s() {
icationtifcancelAllNo }

  ;
 a,
    })ation.dattificfo: no userIn   ult',
  : 'defa soundName,
     ySound: true
      plate,     dabody,
 fication.notiessage: e,
      mitlion.tficat title: noti     edule({
ficationSch.localNotiNotification{
    Push Date) ta, date:tificationDa: Noionficatotiication(nNotifeduleLocal

  sch });
  }a,
   sage.datoteMeserInfo: rem   usult',
   ame: 'defa soundN    
 : true,   playSoundn',
    notificatiobody || 'Newication?.tifnoteMessage.ge: remosa      mesr',
adeus Tr|| 'Nautilion?.title e.notificatteMessagtle: remo ti  tion({
   otifican.localNioatshNotific
    Puny) {ssage: an(remoteMetioNotificahowLocal}

  s    }
  ;
ror)end:', erto backn nd tokeseailed to error('Fconsole.r) {
      erro catch (    }    });

  ),   }     tform.OS,
 Pla   platform:     token,
       
     tringify({ JSON.sdy:      bo
  
        },n/json',atiolicpe': 'appContent-Ty  '       : {
 ders     hea',
   ST method: 'PO {
       r',teregisns/ificatiootile/api/nfetch('/mobawait = se const respond
      backenken to your  // Send to {
     
    try) {ken: stringToBackend(to sendTokenasync
  
 }  });
 age);
  emoteMess, rsage:'mes'Background onsole.log(      cage) => {
Messync (remoteandler(asdMessageHetBackgroun).ssaging(  messsages
  ckground mele ba // Hand });

   
   ge);Messa(remoteionlNotificathis.showLoca{
      tsage) => c (remoteMesessage(asynaging().onM    messessages
 moundegr Handle for   //);

  }ken);
   wToToBackend(neendTokenwait this.s
      awToken);token', ne('fcm_e.setItemyncStoragawait As> {
      wToken) = (nesyncenRefresh(anTokaging().omesssh
    en refre for tok   // Listen

 nd(token);okenToBacket this.sendTnd
    awaiken to backeto    // Send en);
    
oken', tokm_tm('fc.setIteyncStoraget As    awaire token
to S 
    //  oken);
 ken:', t'FCM Tolog(onsole.;
    c).getToken()t messaging(n = awaiconst toke  token
  / Get FCM    /sages() {
 orRemoteMeserFregistnc asy

  
  }   });== 'ios',
 S =rm.Os: PlatfossionrequestPermi   
      },tion);
   :', notificationtificag('Local nosole.lo con   ) {
    onotificatition(nion: funcNotificat on
     onfigure({ion.cushNotificattions
    Pica local notifigure   // Conf   }

 ();
 MessagesorRemoteterFis.regisit th awa
     ted');sion grann permisNotificatioe.log('    consol{
  f (enabled) AL;

    is.PROVISIONtionStatuthorizaAusaging.=== mesauthStatus ||
      HORIZED UTtatus.AhorizationSg.Autgin === messatatusthS =
      aubled ena
    constssion();Permi).requestessaging(s = await mtuauthSta
    const issionequest perm  // Rons() {
  tificaotizeNtiali
  async ini

  }();tificationsitializeNothis.in
    uctor() {onstrss {
  cServiceClaionatotific}

class N;
ny>tring, aRecord<sdata?: ing;
  
  body: stre: string;itla {
  tificationDaterface Notintrt 
expon';
-notificatio-native-pushactom 'reification frshNotort Pu';
impsync-storagec-storage/ave-asynt-natiom '@reacge frtorancSAsyort g';
impessagine-firebase/mtivt-na@reac from 'rt messaging'''imporn  retu
        code"""rviceication sete notifGenera"""
        tr:self) -> s_service(notificationef generate_
    dame__)
    ger(__nging.getLoger = logogg    self.lconfig
    .config =   self
      onfig):ficationC PushNotif, config:__init__(sel
    def     
"""ile appvice for mobfication sernotih ""Pus"ce:
    tionServiNotificaPushs e
clason Servicificati
# Push NotIEXEC)

.S_| stat).st_mode path.stat(hmod(script_cript_path.c      s    
      s():existath.ipt_p  if scr   e)
       k=Truist_oue, exparents=Trr(rent.mkdi_path.pa     script    cript
   / s_dir f.apph = selt_patscrip          :
  ios.sh"]s/build-, "scriptsh"ndroid./build-aiptsin ["scrpt r scri
        foatimport st        le
ts executabke scrip# Ma        
)
        _ioswrite(build   f.        s f:
  a", "w")d-ios.sh/builptsr / "scri_diapppen(self.ith o 
        w'
       
''xcarchive"usTrader.s/Nautil: build/iod completeS buil"iOve

echo rchi          a\\
 .xcarchive sTrader/Nautilu/ios./buildivePath .       -arch\
    =iOS \orm/platfion generic   -destinat       \\
 lease ation Re  -configur  \
       sTrader \tiluNauscheme   -         e \\
workspacer.xcad NautilusTrcerkspa-wocodebuild ive
xarchild Burader

# usTheme Nautil -scorkspacer.xcwsTradeNautilue -workspacan debuild cles
xcoous buildrevi Clean p ios

#

cde..."g iOS Archivinuildcho "B

e/bin/bash'''#! =   build_iosiOS
      for script ild        # Bu        
 
ld_android)ite(bui       f.wr      f:
"w") asroid.sh", /build-andscripts / "elf.app_dir(s  with open 
        ''
     r.apk"
'tilus-trade/android/nau buildplete:ld comd buiroi "And
echoader.apk
tilus-trandroid/naupk ../build/se.aeael-re/appeasputs/apk/reluild/outd
cp app/boi/andr/builddir -p ..y
mkrectorut diPK to outp Apy
# Coase
elessembleRlew a
./gradlease APKuild reclean

# Bgradlew ndroid
./s
cd aus buildn previo"

# Clea APK... Android"Building
echo sh
!/bin/baoid = '''#dr  build_an      droid
ipt for Anild scr        # Bu"""
iptsnt scrand deploymete build """Genera   lf):
     ipts(see_build_scrnerat _ge    def    
additions)
_plist_inforite(       f.wf:
     ") as s.txt", "wtion_plist_addiios/infopp_dir / ".alfh open(se        wit

        
'''>   </array  </dict>
     
    </array>        string>
  ustrader</utiltring>na<s         
       <array>     ey>
       LSchemes</k>CFBundleUR <key           >
tringle</s.mobiustradercom.nautil<string>         </key>
   NameleURLy>CFBund         <ket>
   ic<d
            <array>y>
RLTypes</ke>CFBundleU>
    <keyrray>
    </aring</stioncattifing>remote-no  <stri     >
 stringing</d-processun>backgroring       <strray>
 y>
    <aodes</kegroundMackIB   <key>Utring>
  commands</sice for voeduirreqs is cesac>Microphone ringst
    <y>keption</UsageDescriNSMicrophone   <key>/string>
 scanning<e r QR coded foequir ra access iseram<string>Cey>
    /kscription<ameraUsageDekey>NSC <  
 t</string>g accounadinyour trsecure and uthenticate ce ID to ae Fa  <string>Us/key>
  Description<FaceIDUsage  <key>NS '''
  tions =o_plist_addi    inf
    itionsfo.plist add     # In""
   "urationnfigecific coiOS-spGenerate      """(self):
   _confignerate_ios    def _gele)
    
d_grad(buil    f.write       s f:
  "w") ae",dl.grauild/bd/app"androipp_dir / pen(self.aith o 
        w'''
       e(project)
adlBuildGrulesAppplyNativeMod; apgradle")s.oduletive_m/nandroidform-acli-platy/-communitivect-natea_modules/@rde../no../ile("from: f
apply }}
}}
   scFlavor
 on jmplementati    ise {{
    
    }} el
        }}ok.fbjni'boom.faceoup:'cclude gr     ex
        {{e:+")inermes-engact:hebook.re"com.facmentation(  imple) {{
      esenableHerm if (
    
   SION}}")VERR_FLIPPEplugin:${{co-fresflipper-pper:ook.fli"com.faceblementation(  debugImp  }}")
PER_VERSION:${{FLIP-plugintworklipper-neok.flipper:fom.facebon("clementatiobugImp
    deN}}")PER_VERSIOFLIP{{r:flipper:$pecebook.flipon("com.faImplementatiug
    deb   .1.0'
 iometric:1:bicoidx.biometrn 'andrtatiolemenmpic
    imetrBio 
    // '
   ssaginge-mease:firebasfirebogle.gotation 'com.  implemen'
  nalyticsirebase-a:firebase.google.fom 'conplementati   im.2.0')
 bom:32base-re.firebase:filerm('com.googtfoplaation    implementFirebase
  
    // 
   0"t:1.0.freshlayout:swipereouayrefreshlipex.swidn "androlementatioimp   "
 ndroideact-ak.react:rcom.facebootation "implemen)
    "]"*.jarude: [inclbs", "liree(dir: tation fileT   implemens {{
 enciend
depe}
}}
  }}
    }     se
 eleaingConfigs.rfig signsigningCon         "
   s.pro-rulerd"proguaxt"), .tdroidrd-anle("proguardFiefaultProguas getDoguardFile     pr   
    leaseBuildsRerdInroguanablePifyEnabled e  min
          {{e      releas  }}
   ug
      nfigs.debgCoingnngConfig si   signi        {{
    debug 
     ildTypes {{}}

    bu   sion}"
 verself.config.Name "{ersion       vber}
 uild_numg.bonfiself.crsionCode {       veion
 rskVergetSdxt.taject.e rootProetSdkVersion       targn
 SdkVersioinect.ext.mootProjon rkVersinSd       mile_id}"
 .bundelf.configonId "{s applicati{{
       ig nf defaultCoion

   rskVeSdpile.ext.comojectotPrkVersion roompileSdd {{
    c
androi'
eservic-soogles.g.gm 'com.googlen:apply plugiact"
facebook.rem.ugin: "coly plon"
applicatindroid.appin: "com.apply plugf'''aradle = _g     builddle
   ra # build.g
       
        ty)in_activi.write(ma    f
        w") as f:java", "Activity.r/Maindeilustracom/nauta/src/main/javroid/app/ "andf.app_dir /th open(sel
        wi       '
 }}
}}
''
  );Enabled()Fabricoint.gettureEntryPewArchitecltN    Defau),
    mponentName(CotMain      ge this,
         elegate(
ctivityDactAw DefaultRe   return nete() {{
 yDelegaReactActivitte creategativityDeletAcReacted ecde
  prot @Overri }}

 ";
 tilusTradereturn "Nau() {{
    rntNameponeainComng getMd Striotecteerride
  pr
  @Ov}
State);
  }ancete(savedInster.onCreaupis);
    sthen.show(hScre
    Splastate) {{tanceSInssavedte(Bundle ead onCrcted voiteide
  pro  @Overrty {{

actActiviy extends RenActivitMaiublic class ndle;

ps.Buoid.odr
import ancreen;.SplashSashscreensplo.rn.rt org.devigate;
impotivityDeleeactAcaultRfaults.Def.decebook.reactrt com.fa
impoyPoint;tureEntrhitecaultNewArcults.Defdefat.reaccebook. com.fae;
importelegattivityDactAcok.react.Re.faceboort comy;
impeactActivitreact.Racebook.import com.fe_id};

.bundl.config {selfgecka''paity = f'ivactin_    ma    ivity.java
inAct Ma   #"""
     ationigurc confcifiperoid-senerate And    """G   f):
 onfig(selandroid_cgenerate_
    def _ers)
    formatt.write(   f    as f:
     w") ", "tters.tstils/forma"src/uapp_dir / elf. open(s   with
          '
   ''
};
; })git',
 te: '2-dinu    mit',
our: '2-digi
    h{-US', ring('eneTimeStalturn d.toLoc  re;
) : datee(dateew Dat ? n'string'=== ate  = typeof d  const d=> {
string : ng)| striDate e = (date:  formatTimxport const

e
};ric',
  });'nume day: ,
   rt': 'shoth  monumeric',
    year: 'nn-US', {
  tring('ecaleDateSoLoeturn d.tdate;
  r) : Date(date? new 'string' f date === ypeo= t const d => {
 ng): string ate | striate: De = (dformatDatort const 
expng();
};
.toStriturn value re}K`;
  }
 toFixed(1)ue / 1e3).rn `${(val   retu
 ) {alue >= 1e3(vif 
  
  }M`;ed(1)}/ 1e6).toFix(value urn `${
    rete >= 1e6) {lu }
  if (vad(1)}B`;
 ).toFixeue / 1e9turn `${(val    re {
e >= 1e9)(valu
  if ring => {er): st numbvalue:mber = (mpactNutCoonst formaxport c

evalue);
};.format(n-US')Format('el.Numberurn new Int
  ret => {ring): stnumber= (value: r atNumbermonst fo c

export;}%`;
}Fixed(2){value.to{sign}$turn `$: '';
  re= 0 ? '+' ue > val sign = {
  conststring =>: number): ge = (valuePercentaonst formatrt cpo
exe);
};
valu  }).format(ts: 2,
ionDigimaximumFractts: 2,
    DigiFractionmum  minirrency,
    cu,
  ncy'le: 'currety {
    sUS',Format('en-Numberew Intl.return n=> {
  ing SD'): str = 'Uurrencye: number, c= (valucy Currenconst format= '''export rmatters 
        foons"""nctiity fuilut""Generate      "):
   lfutils(se_generate_ def 
   )
    ding_service.write(tra  f          
") as f:e.ts", "wingServicTrades/"src/servic / self.app_dirh open(     wit
         
  ss();
'''gServiceClanew Tradinice = dingServt const Tra
expor}

  }
nse.data;resporn 
    retuta);', alertDat('/alertspiClient.post this.awaiesponse = a rnst co }) {
   number;
 ice:  target_prelow';
   _b' | 'pricevece_abori  type: 'ping;
  ymbol: str  s
  lertData: {reateAlert(ac c }

  asyn.alerts;
 ponse.dataturn res  re  /alerts');
lient.get('is.apiC await thesponse = r{
    constrts() legetA
  async t;
  }
ta.watchlis response.daturn;
    rehlist')et/watcet('/markent.g this.apiCliaitsponse = aw    const re() {
istetWatchl g

  async
  }ata;onse.deturn respata);
    r, orderDuick't('/orders/qiClient.posait this.aponse = awrespt ons {
    cmber;
  })tity: nu   quan';
 'selle: 'buy' | ;
    sidingymbol: str   srData: {
 r(ordeQuickOrdeplace
  async   }
a.orders;
sponse.dateturn res');
    r.get('/order.apiClientwait thisnse = ast respo   conrders() {
 tO
  async ge
  }
a.positions;.daturn response);
    rets'o/position'/portfolilient.get(is.apiC await thonse = const resp
   ons() {sitic getPo
  asyn }
st;
 hliata.watcresponse.d return st');
   ket/watchliarient.get('/mapiCl await this.t response =   consa() {
 tMarketDatc ge asyny;
  }

 a.summare.datnsrn respotu  re');
  /summary('/portfolioient.getis.apiCle = await tht respons   cons
 {ry() ummaortfolioSnc getP
  asy;
  }
ig;
    })nfurn co ret  }
     }`;
    rer ${tokenon = `Beahorizati.headers.Autnfig
        co{(token)       if token');
m('auth_ge.getIteStorasync= await Aconst token   
     {(config) =>t.use(async requeseptors.ient.intercpiCl
    this.ats to requesd auth token    // Ad    });

t: 10000,
timeou
      _BASE_URL,API  baseURL: ate({
    = axios.creient  this.apiClr() {
   ucto
  constriClient;
 private apceClass {
 radingServilass T
ce/api';
81/mobilt:80alhosp://loc_URL = 'httASE
const API_Be';
ag-stor/asyncync-storageative-as-neacte from '@roragncSt Asyortos';
imp 'axiromrt axios fmpoice = '''irading_serv tce
       rviding Se      # Tra       
  _service)
 icmetrio.write(b f         :
  ") as fce.ts", "wicServimetrio/services/B "src.app_dir /(self  with open
             '
 
  }
}
''   } error);
 tus:',d stac enablet biometrid to se'Failer(ro.er     consoler) {
  catch (erro }   
g());ind.toStred', enableric_enablbiometsetItem('Storage.ait Async {
      aw   tryd> {
 ise<voirom: P: boolean)(enabledtricEnablednc setBiome asy

  static }
  }   e;
urn fals     retor) {
  catch (err
    }ue';d === 'tr enable      return');
_enabledictromegetItem('biyncStorage.= await Asd t enable
      cons
    try {boolean> {: Promise<led()EnabmetricisBioasync tic   }

  sta};
    }
   led',
   eation faiture crage : 'Signa.mess ? errorceof Errorr instanrror: e  erro    ,
  ccess: false      sun {
  tur     reor) {
 tch (err
    } ca};natures, sig{succesreturn      });

  el',
     Text: 'CanccancelButton  
         payload,,
     tMessagepromp        nature({
eSigtrics.creat.rnBiomeis thre} = awaitatus, signt {succes  cons   
    try {ring}> {
 e?: stnaturult & {sigicResBiometrPromise<
  ): ing,: strloadng,
    payage: strimptMess(
    proteSignaturec async creatati
  }

  s
    }};
      d',len faitioele d'Keymessage : rror.? eeof Error nstancerror i   error: alse,
     s: f     succesrn {
   
      retu {ch (error)   } cats: true};
 esturn {succ  re   
    
   lic_key');ubmetric_pm('bioe.removeIteAsyncStoragait       awKeys();
s.deleteiometricrnBs.await thi     
 
    try {t> {uliometricRes): Promise<BdeleteKeys(tic async   sta }


 
    }     };',
  failedKey creation 'sage :? error.mesf Error tanceo insor: errorerr
        false,ss:      succe
    return {
      {tch (error)  } ca  true};
s: {succes     return     
 ;
  ey)licKpubblic_key', iometric_putItem('btorage.sewait AsyncS;
      ateKeys()eacs.crmetrirnBio await this.ey} =t {publicK   consry {
      tult> {
 etricResomPromise<Biys(): c createKetic asyn
  sta }
 }
    };
 d',
      failethenticationge : 'Aur.messaro ? erceof Errorror instan  error: er,
       false  success: {
         return  (error) {
    } catch 
 n {success};     retur    });

 
  'Cancel',nText: celButto
        canssage,   promptMe{
     ePrompt(etrics.simpl.rnBiomwait this = ass}const {succe{
      
    try Result> {se<Biometricmi: Proing)essage: stromptMe(prcatauthentic ynatic as

  st }
  }   ;
 null   returnr);
   :', errock failedtype chetric me'Bioor(console.err       (error) {
atchpe;
    } cryTybiomet    return e();
  ablailrAv.isSensonBiometricsthis.rait yType} = awst {biometr    conry {
  {
    tll>  | nunge<stripe(): PromisometricTync getBi  static asy  }
  }

e;
   return falsor);
     :', errfailedlity check  availabitricerror('Biome console.or) {
     tch (err    } ca
ble;turn availa     re
 ilable();nsorAvametrics.isSernBio await this.e} =t {availabl
      consy {{
    trolean>  Promise<bo):able(ometricAvailync isBitic as;

  starue,
  })ials: tCredentcevilowDe{
    als(veBiometricatieactNcs = new Rc rnBiometriivate statice {
  pretricServiBiomort class g;
}

expr?: strin erro
 s: boolean;ucces
  ssult {ricReiometace Bxport interfage';

esync-store/a-storag-asynctivet-nareace from '@yncStorag;
import Astrics'ive-biomenateact-s from 'rtricmeveBioeactNati''import Rvice = 'metric_serbio       
 Serviceetric Biom      # ""
  s" moduleervicee snerat"Ge  ""   :
   ces(self)_servienerate
    def _g
    )_cardite(metric     f.wr f:
       w") as", "sxtricCard.tomponents/Me/ "src/c.app_dir  open(self with      
        
 '''d;
artricClt Met defauexpor
};


  ); </View>   }
   )ew>
   </Vit>
        </Tex        | 0)}
  gePercent |ntage(chanrcePe  {format         t}>
 hangeTexyles.ct style={st  <Tex>
               /Color}
   r={change     colo      16}
 size={            
nding-down'} 'treing-up' :ive ? 'trend={isPosit        name    n
 <Ico  r}>
       taineangeCon={styles.ch<View style        ed && (
ndefinchange !== u      {}</Text>
ue}>{valueles.valstyle={sty     <Text e}</Text>
 le}>{titl{styles.tit<Text style=     
 , style]}>containeres.styl{[ style=View  <turn (
  });

  re     },
nLeft: 4,
   margior,
    ngeCol  color: cha
    e: 14, fontSiz    xt: {
   changeTe,
  
    }: 'center',nItems   alig  ,
 tion: 'row'  flexDirec: {
    ontainer
    changeC  },
  om: 4,ott    marginB,
  colors.textolor: theme.     c
 : 'bold',  fontWeight  4,
   fontSize: 2   
  e: {
    valu
    },ttom: 8,Bo   margin   econdary,
tSolors.tex.c theme color:4,
     ze: 1   fontSile: {
     tit
  
    },rs.border,: theme.colorColor      borde
rWidth: 1, borde16,
       padding: ,
    : 12rderRadius     boce,
 ors.surfa.colme thedColor:ckgroun {
      baner:    contait.create({
tyleSheet styles = Scons;

  lors.errorme.couccess : the.colors.semeositive ? thColor = isP change 0;
  const>=hange || 0) ositive = (c
  const isPeTheme();
 = us {theme}onst> {
  c) =
}style,rcent,
  changePe,
  
  changee, valu  title,
 ({
 = s>rdPropMetricCa.FC<eact RcCard: Metri
conste;
}
iewStylle?: V
  stymber;nt?: nugePerce
  chan number;ange?:  chring;
stlue: ;
  vangle: stri titrdProps {
 e MetricCarfacte

inrs';ils/formattem '../utntage} frocermatPerport {fontext';
imContexts/Themeco from '../ {useTheme}
importcons';
s/MaterialI-vector-iconct-nativeon from 'reart Icpoimative';
ct-n 'rea} fromViewStyleStyleSheet, , Text, ew {Virtt';
impo'reacm  React fromport = '''iard_c      metricnent
  Compo Card   # Metric
      nts"""oneeusable compnerate r""Ge     "self):
   onents(compenerate_
    def _g   d_screen)
 hboar.write(das    f   :
     ") as f", "wreen.tsxScoardhbDaseens/main//scrdir / "srclf.app_with open(se     
          '''
 rdScreen;
t Dashboaulrt defa;

expo);
}</View>
  
    /ScrollView>      <View>

 </     } />
  {marketDataiew data=Overvket      <Mart>
    /Texerview<Market OvctionTitle}>={styles.se <Text style
         .section}>{styles<View style=}
        ew */rviarket Ove  {/* M
      
 </View>>
       View       </          />
}
     /} to orders *Navigate* ={() => {/ress  onP       ers"
     "Orditle=         t"
     oryicon="hist             
 ButtonckAction   <Qui      />
       }}
         */ist watchlavigate to N {/*ss={() =>   onPre       list"
    Watche="itl          tlity"
    on="visibi    ic      on
    ctionButt<QuickA        
         />     een */}}
  l scr selgate tovi/* Nass={() => {     onPre"
         "Selltitle=         t"
     care-shopping-="remov  icon          tton
  kActionBu      <Quic/>
                 /}}
 een * buy scrte toiga {/* Nav =>() onPress={     "
        e="Buy     titl       
  rt"g-ca-shoppinadd  icon="          tton
  nBuActio      <Quick     ow}>
 nsRkActioles.quicstyiew style={       <V   /Text>
 Actions<le}>QuicknTites.sectiotyle={styl <Text s   }>
      s.sectionle={style <View sty     
  ctions */} A  {/* Quick      

iew>      </V
  View>    </             />
 8}}
     t: marginLef: 1,yle={{flex        st  || 0)}
    ngPower mary?.buyirtfolioSumrrency(poue={formatCu   val        r"
   ying Powele="Bu  tit      
      MetricCard         <
   >     /   t: 8}}
     marginRighx: 1,fle   style={{      }
      || 0)?.cashSummaryy(portfolioencormatCurr   value={f      "
     itle="Cash       t    ricCard
     <Met          
etricsRow}>yles.mw style={stie       <V/View>
   
          <  />     
     ft: 8}}inLe 1, marg{flex:le={   sty   
        rcent || 0}dayChangePe?.aryolioSumment={portfgePerc     chan         || 0}
 nL.dayPary?oSummportfoli   change={     0)}
      ?.dayPnL || oSummarytfoliy(porCurrencormatvalue={f          "
    &Ltle="Day P   ti    rd
       tricCa     <Me/>
          }
         ht: 8}1, marginRigflex:  style={{        || 0}
     cent ayChangePer.doSummary?olircent={portf    changePe          }
yChange || 0.dary?tfolioSumma={porge chan              || 0)}
lue?.totalVaoSummaryncy(portfoliormatCurre    value={f        
  tal Value""To   title=          etricCard
          <MRow}>
   metrics={styles.iew style <V        Text>
 lio</>Portfoe}nTitlctioles.sele={styext sty    <T}>
      ectionle={styles.s sty  <View    ary */}
  rtfolio Summ Po   {/*    
     >
    >
        }nRefresh} /esh={ong} onRefrshig={refrerefreshinontrol hC   <Refres  ol={
     ntrreshCo
        reflContainer}rols.sclele={sty        sty
lView <Scrol   r}>
  taineconyles. style={stViewurn (
    <});

  ret},
    om: 16,
  Bott      margin
round',t: 'space-aonten    justifyC: 'row',
  tionflexDirec      {
ow: nsRuickActio q  },
   16,
  ginBottom:   marn',
    ee'space-betwent: yContjustif',
       'rowtion:Direc
      flexcsRow: {etri   },
    m,
 ttom: 16    marginBo  xt,
rs.teoloor: theme.col,
      ct: 'bold'   fontWeigh  : 20,
   fontSizee: {
     sectionTitl
   
    },ttom: 24,    marginBo  on: {

    secti,
    },adding: 16  p  ainer: {
  rollCont  sc     },
,
 ndgrouacks.bme.color theoundColor:kgr  bac
    ex: 1,
      flr: { containeate({
   yleSheet.cre Styles =st
  const  };

 lse);shing(fa  setRefreket()]);
  refetchMartfolio(), chPore.all([refetmist Pro;
    awaing(true)efreshi   setR
 => {) async (efresh =  onRonst;

  c  )
    }
y 5 secondsesh ever0, // Refr500chInterval:   refet  ,
    {
  atatDtMarkeService.geading
    Tr',marketData    'seQuery(
= uket} ar refetchM, refetch:arketDatast {data: m
  con
 ); }
 onds
   very 30 sec Refresh e0, // 3000tchInterval:
      refe
    {y,olioSummarce.getPortfadingServi
    TrSummary',iool'portf(
    ryQueseio} = utfol: refetchPor, refetchlioSummaryfo {data: port;

  constalse)ate(fSt = useeshing]Refr, set[refreshingst ;
  coneme()eThheme} = usst {t{
  con) => = (C : React.FhboardScreen
const Dasrview';
ts/MarketOveomponenm '../../c froOverviewort Market
imponButton';QuickActinents/ompo./../c'.from tionButton t QuickAcard';
impornts/MetricCne./compom '../.Card frort Metric
impors';rmatte/utils/fom '../..e} froagPercentrmatforency, urrt {formatCvice';
impoadingSerces/Trrvi/se/.. from '..ce}Servirt {Tradingpo';
imxtte/ThemeConntextscofrom '../../{useTheme} port ns';

imaterialIcoicons/Mve-vector-eact-natirom 'rn fport Icory';
imt-quefrom 'reaceQuery} rt {usive';
impoact-nat 'reromy,
} fbleOpacitToucharol,
  eshContt,
  Refree
  StyleShiew,rollV
  Scxt,ew,
  Te  Vi
import {
 'react';} from, useStateffecteact, {useE R= '''importen oard_scre  dashbeen
      oard Scr  # Dashb         
  
   gin_screen)rite(lo  f.w       as f:
   x", "w") tsinScreen.ns/auth/Log"src/screer / .app_dith open(self      wi   
  
     ;
'''ginScreent default Lo
expor
  );
};
idingView>dAvoboar </Keycity>
   leOpaabuch
      </Toxt></Teon
        Authenticatimetric Use Bio         nText}>
 ttoicBus.biometryle={stylestText        <>
 ricLogin}dleBiomethanPress={      on  ton}
icButetrioms.b{style  style=    y
  acit<TouchableOp
      eOpacity>
abl    </TouchText>
     </     
 : 'Login'}.'g in..g ? 'Logginloadin   {>
       nText}utto.loginB{stylesle=   <Text stying}>
     bled={load      disa
  andleLogin}ess={hPr   onon}
     nButtogi={styles.l     styleOpacity
   lehab    <Touc

  >iew/V  <>
    iew  </Vty>
      chableOpaci       </Tou  >
  /          ondary}
 lors.textSeceme.co={th      color       size={24}
      }
         lity-off': 'visibility' 'visibissword ? owPaame={sh   n         
  Icon          <  rd)}>
!showPasswoassword(owP() => setShonPress={        con}
    eIyles.ey   style={st         pacity
<TouchableO  
         />         ={false}
utoCorrect         a"
   "noneapitalize=   autoC    
     rd}sswoPatry={!showEnText secure       ndary}
    coxtSee.colors.tehemtColor={taceholderTex     pl     
  "assworder="Enter pplacehold            sword}
Text={setPas onChange      word}
     {pass      value=    
  t]}swordInpu.pasylesnput, sts.i{[stylee=     styl  nput
        <TextI>
       er}rdContainles.passwo{styw style=     <VieText>
   rd</swolabel}>Pas{styles.<Text style=       r}>
 putContaine={styles.inew style<Vi>

        </View    />
    }
    rect={false   autoCor"
       ize="nonetoCapital    au     ondary}
 ors.textSecr={theme.collderTextColo  placeho      me"
  serna"Enter ulder=aceho         pl}
 ernameUsText={set  onChange
        e}rname={use       valuput}
   .inylesle={st   styut
           <TextInp   /Text>
 >Username<l}abees.l{stylt style=Tex     <
   ontainer}>les.inputCstystyle={View      <>
      
 ext/Tus Trader<go}>Nautil.lolest style={sty      <Texheight'}>
ing' : '? 'padds' S === 'iorm.Ofor={Platbehavio   }
   nercontaile={styles.tyw 
      sieoidingV <KeyboardAv  eturn (
  });

  r  },
 ld',
  ht: 'boWeig      font6,
Size: 1   fontrimary,
   eme.colors.pthr:   colot: {
    cButtonTexometri  },
    biary,
  s.primme.colorerColor: the   borddth: 1,
   Wiorder      b15,
 marginTop:   
   nter',ems: 'ce     alignItding: 15,
 ad     p
 ,s: 8borderRadiuace,
      rs.surf theme.colooundColor:ckgrba   tton: {
   ometricBu
    bi   },,
 'bold'tWeight:    fon: 18,
       fontSize#fff',
   color: 't: {
     TextonBut
    login,
    }0, 2p:   marginToer',
   : 'centlignItems a   5,
  adding: 1 p    dius: 8,
 borderRa  ry,
    maors.pricololor: theme.groundC      backButton: {
  login    },
  ,
ight: 15  r',
    : 'absolute   positionn: {
   eyeIco
        },lex: 1,
 {
      fsswordInput: },
    pa
   er',s: 'cent  alignItem',
    on: 'rowrectiflexDi      iner: {
tadCon    passwor
    },
lors.border,theme.coerColor: ord  b 1,
    rderWidth:6,
      boize: 1  fontS
    s.text,.colorlor: theme  co5,
    padding: 18,
      us: borderRadice,
      colors.surfaeme. thoundColor:ackgr      b: {

    input   },6,
 e: 1 fontSiz   8,
  Bottom:       marginext,
me.colors.tlor: the {
      co label: },
   20,
   rginBottom:     ma: {
  utContainerinp      },
: 40,
  marginBottom     
 r',n: 'centeextAlig    ty,
  s.primartheme.color  color: ld',
     'bot:   fontWeigh32,
   ze: fontSi {
      o:,
    log
    }ding: 20,     padcenter',
 tent: 'Con   justifyround,
   ckge.colors.baemthroundColor:      backgex: 1,
 
      flntainer: { coe({
   reatStyleSheet.cstyles = t ns };

  co    }
  again');
'Please tryed', ation Failuthenticrt('A.ale
      Alerterror) {atch (} c    }
    );
  etricLogin(om    await bi     {
.success)  if (result
    nt'); accouccess yourate to a'Authentichenticate(ce.autcServietri Biom= awaitnst result   co  }

      
  rn;      retud');
  nd passworrname ae usee us'Pleasable', c Not Availtrilert('Biome  Alert.a
      ) {Available!is   if (able();
   etricAvailisBiomtricService.t Biomelable = awaiAvainst is     co {
    try () => {
 n = asyncLogimetricst handleBio
  con  }
  };

  );falsetLoading(se
      } finally {');
     or passwordameernlid usva, 'Inin Failed''Logt.alert(      Alerrror) {
h (eatc    } c);
e, password(usernam await login  try {
   
    ue);(tretLoading  }

    s
  eturn;    r  ssword');
d paanname serenter both u'Please 'Error', rt.alert(  Ale    word) {
 !passsername ||  if (!u> {
  sync () =eLogin = ast handl  con);

useTheme(eme} = const {thAuth();
  in} = useetricLog{login, biomnst co 
  (false);
 eState us] =sswordd, setShowPaowPassworshnst [se);
  couseState(fal = ing]setLoadoading, 
  const [l');= useState('ord]  setPasswrd,t [passwo cons);
 e(''seStat u =me], setUsernarnameonst [use  c=> {
) act.FC = (Screen: Re Loginconst';

ricServiceces/Biomet../../servi 'ice} frommetricServ {Bioxt';
importonte/ThemeC./contextsfrom '../.seTheme} import {uhContext';
/Aut../contextsfrom '../useAuth} import {ns';

ialIco/Matertor-iconst-native-vecfrom 'reacimport Icon 
-native';'reactom m,
} frPlatforView,
  dingvoiyboardAt,
  Ke AlerleSheet,
 y,
  StyitouchableOpacput,
  T
  TextIn  Text,View,
{
  ;
import  'react'romeState} f {useact,t Rmporcreen = '''i   login_s   een
  cr S     # Login   ents"""
reen compone sc"Generat     ""lf):
   ns(se_screeenerate _g 
    def
   tor)pp_naviga  f.write(a       as f:
   ", "w") or.tsxigat/AppNavc/navigationir / "srn(self.app_dope     with   
   '''
      igator;
 AppNav default
export;
r>
  );
}gatotack.Navi
    </S
      )}        </>/>
      
    })}mbol} Chart`rams.syte.patle: `${rou) => ({ti({route}  options={     en}
     ChartScre={component         
   " "Chart    name=     
   een Scr     <Stack.         />
      y'}}
Historrder 'O{title: ={ons       optin}
     storyScreeOrderHimponent={         coory" 
   rHiste="Ordeam           neen 
 Scr     <Stack.  />
           
  ace Order'}}: 'Pltitleons={{ti   op      
   n}creetrySEn={Order  component    
       rEntry"Ordee="  nam           
creen   <Stack.S     />
       } 
     own: false}={{headerSh   options      or} 
   gatnTabNavint={Mai compone      " 
     ain    name="M        een 
  <Stack.Scr>
              <
   ) : (</>
                  />
 
    n'}}atioc Authenticup Biometrile: 'Set{{tit options=       een}
    icSetupScriometrmponent={Bco       
     up" metricSetBio   name="         ck.Screen 
       <Sta/>
              false}} 
derShown:tions={{hea        op} 
    nScreenponent={Logiom      c    
  "Auth"    name=      
   Screen ck.      <Sta    <>
    
    ted ? (tica {!isAuthen     }>
},
      }   
     ackground,me.colors.b: thekgroundColor     bac
     : {yle    cardSt
    xt,teeme.colors.r: thColont    headerTi },
    
       e,aclors.surfe.co themolor:ckgroundC    ba{
      derStyle:    hea    
 nOptions={{      screegator
tack.Navi   <S
 eturn ( r
 heme();
seTheme} = u
  const {tuseAuth();ticated} = isAuthenconst { () => {
  C =eact.FNavigator: Rpp

const A  );
};tor>
ga.Navi/Tab  <} />
  eenSettingsScr={ent" componngse="Settien nam<Tab.Scre    >
  reen} /ScWatchlistmponent={ist" coe="Watchlam nab.Screen      <T>
een} /ingScrt={Tradomponen" cngname="Tradireen     <Tab.Scn} />
  reelioScPortfot={onenmpfolio" coame="Portab.Screen n  <T
    reen} />shboardSct={Da" componenboardme="Dashnaab.Screen }>
      <Tt,
      })e.colors.texr: themtColo headerTin     ,
        }surface,
  eme.colors.thoundColor: kgr    bac  le: {
    eaderSty h               },
r,
lors.borde.cor: themerTopColo borde      rface,
   olors.su theme.cor:oundColackgr         byle: {
 BarSt  tab      ary,
textSeconds.orme.colthe: tColortiveTinbBarInac
        taimary,s.prtheme.colorntColor: ActiveTiar        tabB
       }, />;
 or={color}e} colize={sizme} sonNaon name={icurn <Ic ret
            }
       = 'help';
me nNa         ico     t:
efaul        dbreak;
               gs';
   ttine = 'seconNam           ings':
   Settie '     cask;
            brea        ;
 ility'sibName = 'viicon          
    list':se 'Watch         ca   ak;
   bre        ng-up';
   trendi ' =Name       icon       'Trading':
      case ;
       break   
          et';alance-wall'account-b= ame     iconN
          ortfolio':    case 'P     ak;
   re     b;
         'dashboard' iconName =         
     board':e 'Dash      cas    e) {
  te.namitch (rou        sw
  
ing;ame: strnN ico      let {
    ize}) => sd, color,on: ({focusebBarIc    ta> ({
    {route}) =s={(creenOption      stor
viga
    <Tab.Na  return (Theme();

 use} =const {theme{
  () => eact.FC = Navigator: Rt MainTab

cons);ramList>(<MainTabPaavigatortomTabN = createBot
const TabramList>();RootStackPaator<igeateStackNavack = crSt

const ined;
};: undeftings
  Setned;ist: undefi;
  WatchlefinedTrading: und;
   undefinedortfolio: Pfined;
  undeashboard: = {
  DamListarMainTabPort type 

exp};ned;
 undefitup:ometricSe;
  Bi string}ol: {symbt:Char
  undefined;: History Orderring};
 ?: st {symbolerEntry:;
  Ordefinedund
  Main: efined;h: und Aut{
 st = ckParamLiStaype Rootport t
ex
reen';ing/ChartScad/screens/tr..n from 'ChartScree';
import enryScreerHistordding/Otra'../screens/creen from rHistorySrdemport Ocreen';
itrySg/OrderEnns/tradinscree../m 'froyScreen  OrderEntrimport Screens
/ Trading
/creen';
ngsSn/Settiscreens/mai '../ fromencresSort Settingeen';
impistScr/main/Watchlscreens./m '.en frotchlistScre Waportn';
imradingScree/main/Tens/screrom '..en fradingScremport T';
iolioScreenmain/Portfns//screefrom '..een ioScrrtfolmport Po
in';hboardScreein/Das/screens/ma.. 'creen fromboardS
import DashScreensn ;

// Main'upScreeicSettrh/Biome/aut/screens'..een from pScrtucSeometri;
import Bien'ginScreuth/Lons/acree from '../seent LoginScrimporScreens
// Auth 
t';
exhemeCont/contexts/T from '..seTheme}
import {uhContext';exts/Aut '../cont fromseAuth} {u;

importons'erialIcor-icons/Matative-vectact-n from 'remport Icon
itabs';tion/bottom-navigareact-om '@avigator} frteBottomTabNeaimport {crn/stack';
navigatioreact-} from '@orStackNavigatport {create
imm 'react';React fro'''import navigator =  app_""
       tructure"igation snavGenerate    """):
     ion(selfe_navigatenerat
    def _g
    p_tsx) f.write(ap        
   s f:w") a", " / "App.tsxp_diropen(self.apth wi         
  
'''
     lt App;defau

export >
  );
};ViewdlerRoot</GestureHaner>
    ClientProvidery   </Qu
   Provider>Theme </      
 Provider> </Auth     er>
    nProvidtio  </Notifica
          ontainer>NavigationC        </  >
    pNavigator /    <Ap         a" />
   or="#1a1a1roundColnt" backg-contee="light barStyl <StatusBar           ainer>
    igationContNav  <     r>
       ionProvideNotificat     <  ider>
     Prov<Auth         ovider>
 <ThemePr    nt}>
    ryClieueer client={qidroveryClientP  <Qu}}>
    x: 1{fleew style={RootVitureHandleres
    <G return ( }

 wing
 s shosh screen i/ Splaurn null; /
    retized) {Initial
  if (!is   }
  };
();
 reen.hide    SplashSctart.');
  lease respp. Pe alize th initialed torror', 'Failization Enitia'I.alert(Alert  r);
    erro:',  erroritializationApp in('rorerconsole.
      h (error) {} catc);
    Screen.hide(Splash     een
  scride splash  // H    );
      
d(truelizesInitia     setI;
      
 Supported)tricmee(bioailablicAvtBiometr      seailable();
AvsBiometricce.icServiit Biometrirted = awaetricSuppo const biomty
     availabiliic iometrCheck b    // 
  
      );ifications(pPushNot setu   awaits
   ficationsh notip pu     // Setu     
 ();
 nitializeApp  await irvices
    ize app seialInit //      {
 > {
    try =()= async cation lizeApplinitiaconst i, []);

  
  });ion(pplicatalizeAiniti> {
    ect(() =
  useEff;
false) = useState(ble]etricAvaila, setBiomleicAvailabetronst [biom
  cte(false); useStaialized] =sInit, setIlizedst [isInitia  con{
 => FC = ()React.nst App: ,
});

co }    },
 utes
 min00, // 5 5 * 60 * 10Time:     staletry: 3,
 
      reies: {
    quer: {ptions defaultO
 ryClient({new QueyClient = nst quer
covice';
erBiometricServices/om './src/sce} frServiiciometr
import {Be';onServiccatis/Notifirc/service} from './sificationsotetupPushNort {s';
impervicees/AppSc/servic './srfromtializeApp} 
import {inigator';ppNavi/Aation/src/navigor from '.vigatAppNat';
import nContexNotificatioc/contexts/om './srer} fridProvNotificationport {ontext';
imtexts/ThemeCc/con'./srm der} frohemeProvi {T
importontext';hCexts/Autntm './src/co frohProvider}
import {Auter';
ndl-have-gesturect-natieaom 'rw} frRootVielerestureHandport {G;
imcreen'e-splash-sivreact-natm 'een frot SplashScrpor-query';
imrom 'react} fientProvidert, QueryClyClienerQut {ve';
imporgation/natit-navi@reac 'ainer} fromtionContvigaort {Na
impive'; 'react-natt} from, Aler{StatusBar
import eact'; 'rfromState} sect, ut, {useEffeport Reac'im''app_tsx =       "
  ponent""ain App comerate m   """Gen
     f):selnt(_app_componeef _generate   
    ddent=2)
 ig, f, inmp(ts_confon.du js    
        as f:", "w")on"tsconfig.js/ pp_dir  open(self.a       with 
    
     }  
              ]s"
   ig.j"jest.conf            ",
    jsfig.on "metro.c           
    ig.js",abel.conf        "b     ",
   ules_mod  "node             
 ": [exclude  "        
        },     }
              "]
   s/*type": ["/types/*"@               
     ,"utils/*"]ls/*": [    "@/uti              *"],
  es/ ["servic/*":esservic     "@/               ],
/*""screensens/*": [@/scre"                    *"],
onents/["compts/*": mponen"@/co                *"],
    "": [/*     "@             : {
  s"     "path           "./src",
"baseUrl":          ",
       ": "esnext"target         e,
       ru": Trict       "st    ,
      True "noEmit":      
         ode",on": "nolutiesoduleR        "m       "],
 ["es2017  "lib":         ",
      ve-natiact "re":sx"j               ,
 es": TruelatedModul     "iso         
   True,erop":ntuleIsMod"e           True,
     ports": aultImtheticDef"allowSyn        ,
        ": True "allowJs         : {
      Options"ler "compi           ,
onfig.json"tscact-native/@tsconfig/reends": "    "ext     fig = {
      ts_con
     ""n"configuratiopeScript Ty"Generate "        "fig(self):
pescript_conerate_tyf _gen
    de   ;")
  indent=2)}g,confidumps(babel_ts = {json.xpor.e"modulee(f   f.writ
         ) as f:"ig.js", "wonfbel.cr / "baself.app_dih open(
        wit           }
          ]
  gin"
     nimated/plutive-rea  "react-na         ": [
     plugins      "    t"],
  eseel-prive-babeact-nato-r"module:metrresets": [         "p = {
   igbabel_conf        on"""
nfiguratiabel coGenerate B""        "elf):
onfig(sabel_c _generate_b  
    defig)
  nfo_corite(metr f.w    :
       ) as f", "w"jsconfig.r / "metro.di(self.app_h open   wit     
     '
   onfig);
''name), cfig(__dirltConDefauConfig(get mergele.exports ={};

modust config = 
con */}
nfigig').MetroCotro-confport('metype {im*
 * @ion
 /configuratetro/docso/m.ibook.githubtps://faceon
 * httirao configu * Metr/**
);

etro-config'ct-native/m@reae('g} = requirmergeConfiConfig,  {getDefault''const 'tro_config =      me"
  ""figuration bundler cone Metro""Generat   "    ):
 elfnfig(so_coate_metrner
    def _ge)
    ndent=2p_json, f, ion.dump(ap  js       ) as f:
   n", "w"jsopp._dir / "aapph open(self.      wit    
 }
       }
                         ]
        ssaging"
 meirebase/t-native-f"@reac                 /app",
   ive-firebasereact-nat    "@             [
   ": ins     "plug        },
                ng"
   icon.pges/favimas/"./src/asset": vicon"fa                ": {
    eb "w                   },
                   ]
         "
    OCK "WAKE_L                   ",
    _COMPLETED_BOOTECEIVE       "R          
       VIBRATE",          "          ",
    CORD_AUDIO "RE               ,
        MERA"      "CA              ",
    RPRINTINGEUSE_F        "           ",
     IC"USE_BIOMETR                     [
   s": onmissi   "per               ,
  berld_numfig.bui": self.consionCode"ver           ,
         g.bundle_idf.confielage": sck"pa           ,
            }              
   " "#1a1a1andColor":ou "backgr                   
    ",e-icon.pngges/adaptiv/assets/ima": "./srcoundImage"foregr                        {
 n":adaptiveIco        "            d": {
 "androi              },
              
     }                  
s"ce command for voiireds requone access i: "Microph"eDescriptioncrophoneUsagMi     "NS                  ning",
 R code scanred for Qess is requiCamera accon": "criptieDesraUsagCame        "NS           ",
     accountr trading cure youicate and sehentce ID to autUse Fa"ion": scriptageDeDUs"NSFaceI                   : {
     list"   "infoP            ,
     ld_number).buiigconfelf.ber": str(suildNum"b                 d,
   g.bundle_iconfi self.dentifier":leI  "bund           ue,
       et": TrportsTablsup     "      
         "ios": {                   ],
           
  **/*"       "        
      [s":erntttBundlePa    "asse              },
             : 0
 ut"eoimToCacheTfallback          "
          pdates": {       "u    
            },        1a"
 ": "#1a1aolorgroundC  "back            ,
      tain""coneMode":    "resiz                ng",
 /splash.pes/imagsrc/assets"./mage":          "i        
   sh": {  "spla     
         ng",con.pmages/ic/assets/ion": "./sr       "ic       it",
   "portration":orienta          "     ersion,
 .config.vlfersion": se        "v
        rader",nautilus-tug": ""sl            name,
    fig.app_": self.conme     "na           
expo": {          "_name,
  fig.applf.con seName":  "display          pp_name,
onfig.ame": self.c        "na = {
    son   app_j     "
ility""compatib Expo pp.json forte aGenera"      ""n(self):
  sorate_app_jene    def _g 
  
 nt=2)def, ine_json, kag(pacmpjson.du         
   :s f"w") aon", .jsgeka"pacr / self.app_dien(ith op
        w }
                }
          "
 act-native": "re  "preset       
       ": {"jest  
                    },0.7.0"
   "^2etox":      "d         
  "4.8.4",pt":ritypesc        "      ,
  : "18.2.0"enderer"act-test-r"re              
  "^2.4.1",prettier":   "         
     ",6.5"0.7: preset"-babel--native"metro-react           ",
     : "^29.2.1st"      "je        .0",
  ^8.19"eslint":  "           ",
    29.2.1"^el-jest": ab        "b     
   "^2.0.2",l": s/numera@type"              .0.0",
  ": "^18endererest-rs/react-ttype  "@            ",
  .0.24ct": "^18pes/rea     "@ty  ,
         "^3.0.0"native": act-tsconfig/re   "@       0",
      ": "^0.72.configetro--native/mact@re       "         .72.0",
fig": "^0-con/eslintve"@react-nati        
        20.0",: "^7.l/runtime" "@babe             .0",
  7.20nv": "^et-ebel/pres@ba"          
      .0",e": "^7.20abel/cor    "@b      
      cies": {Dependen"dev            },
            6"
l": "^2.0.    "numera          ",
  : "^2.30.0s"  "date-fn           .0",
   : "^1.2p"      "yu  
        7.45.0",: "^-hook-form""react              0",
  : "^4.3.and" "zust            0",
   ": "^3.39.-query   "react         7.0",
    ^4.": "-client"socket.io      
          ^1.4.0",os": " "axi             
  "^0.2.7",": jobnd-groue-backact-nativ  "re      
        ^5.2.1",nfo": "ork-ive-netwnatict-      "rea        1.5.0",
  ocker": "^tion-ltative-orienct-na"rea      
          0",3.3. "^-screen":e-splashnativact-"re              4.3.0",
  : "^h"-local-autt-native"reac          ",
      1 "^8.1.":ication-push-notifeact-native         "r     0",
  ^3.8.": "rmissionsive-pereact-nat "               
10.8.0",info": "^e-device-ativeact-n      "r         8.1.0",
 ": "^ychainve-ke"react-nati             ,
   "^3.22.0"reens": e-scact-nativ "re              0",
 .7.ext": "^4e-area-contive-safreact-nat  "            3.3.0",
  ": "^atednim-native-rea"react                ",
2.02.1dler": "^e-han-gestur-native"react     
           ^13.9.0",": "tive-svg-naact     "re       ",
    6.12.0"^hart-kit": ative-creact-n  "             10.0.0",
 : "^tor-icons"ecact-native-v     "re          ",
 18.0.0s": "^icbase/analyt-firenativeact-       "@re        ",
 ^18.0.0ng": "ase/messagifirebve-tiact-na"@re        ",
        .0.0 "^18/app":rebasefie-act-nativ "@re          
     ",0.0ics": "^3.ive-biometreact-nat   "r             ,
1.19.0": "^age"sync-stornc-storage/aasyact-native-"@re              ,
  "^6.5.0"m-tabs": bottoon/tinaviga   "@react-             0",
.3."^6": ck/stat-navigationac   "@re             ^6.1.0",
e": "ivn/natavigatiot-n@reac     "        ,
   : "0.72.0"ve"ti  "react-na          0",
    2. "18."react":        
        cies": { "dependen          },
        e"
     ve archivhiTrader.xcarch NautilushivePat-arcrm=iOS c/platfogenerion tidestinaelease -uration Riger -confilusTradscheme Naut -workspaceader.xc NautilusTraceld -worksp&& xcodebui"cd ios d:ios":   "buil          ",
    leReleaseassemblew ad& ./grandroid & "cd droid": "build:an      ,
         ,.tsx"sx,.ts.js,.jint . --ext sl"lint": "e            
    jest",t": "    "tes         
   e start",tiv-naeact"r"start":               os",
  ve run-i-nati": "react   "ios           roid",
  -and runt-nativereacoid": ""andr                s": {
ipt       "scr
     ": True,   "private     
    .version, self.config"version":          ",
  -mobilelus-tradernauti"me":     "na{
        n = ge_jso   packa
     json"""ge. packate""Genera   "
     json(self):_package_nerate    def _ge
    
=True)e, exist_ok=Truarents.mkdir(py) directorapp_dir /elf.(s          tories:
  in direcry recto   for di      
        ]
    
   tests__" "__      
     ",xcassetsder/Images.autilusTra   "ios/N   ",
      derusTraNautil"ios/      ",
      /drawableesn/r/mairoid/app/src    "and      es",
  n/res/valumaiid/app/src/   "andro      ",
   strader/com/nautiluc/main/javap/sr/apid    "andro    ",
    ontsssets/f    "src/a  
      s/images",/asset    "src        ",
"src/types         
   ",ontexts/c"src        ",
    rc/hooks"s            ls",
"src/uti  
          rvices",se "src/      
     ation",c/navig "sr
           ",enscresrc/s       "",
     ntsonerc/comp      "s
       [s =rie     directo"
   tructure""y sectordir"Create app  ""):
       ure(selfucttr_sirectory_dcreate
    def _
    fully")cessted suce generastructurNative app React r.info("self.logge                
scripts()
ld_enerate_builf._g    sets
    d scripuilnerate b    # Ge   
    
     config()erate_ios_f._gen     selig()
   android_conf_generate_lf.
        seionsnfigurate corate nativ   # Gene   
     s()
     tilrate_uneelf._ge)
        ses(rate_servicgene     self._
   s()nentate_compoeren._gelf s)
       te_screens(nera   self._ge)
     tion(_navigagenerate self._  ent()
     on_comperate_appelf._gen s      ents
 ative compon Ne ReactGenerat#      
         
  nfig()script_conerate_type    self._ge
    ig()_conferate_babelgen    self._fig()
    o_connerate_metr._ge  self()
      e_app_jsonf._generat   sel     ge_json()
erate_packalf._gense      files
  ation onfigurerate cGen #         
 
      structure()y_rector_diatere_celf.      s
   structurete directory     # Crea    
      
 cture...")ruapp stt Native eacing R("Generatinfoer.logg    self.   "
 e""app structurive  Natte ReactompleGenerate c"""      (self):
  pp_structuree_a generat 
    def  le")
 der_mobitilus_traauPath("napp_dir = f.       sele__)
 amger(__noglogging.getL.logger =         selffig
on= cself.config     g):
    ppConfiig: MobileA, conf(selfnit__   def __i
    
 tion"""licae mobile appReact Nativ"Generate 
    ""or:nerattiveAppGeactNa

class Retr
ver_key: sfcm_ser
    trd: s apns_team_i  r
 _id: st    apns_key
_name: stroid_package   andrr
 id: st_bundle_
    iosct_id: strprojefirebase_"""
    ntioraonfiguon cotificati""Push n"    :
cationConfigshNotifiss
class Pu

@datacla int = 33
_version:sdket_ targ
    21rsion: int =roid_ve  min_and"13.0"
  : str = ios_versionmin_t = 1
    d_number: in buil0.0"
   str = "1.: sion verle"
   obiustrader.mm.nautilstr = "coe_id: ndlbu   
 "rader"Nautilus Tme: str =    app_naon"""
 iguratinfe app cobil""Mo
    "nfig:ppCoeAils Mob
clasaclass
@datFalse

ILABLE = VA FLASK_Aror:
   ortErt Imprue
excepVAILABLE = TK_A
    FLASRS import COcorsk_rom flast
    ffy, requessoniask, jport Flsk imfrom fla:
    uid

tryrt uath
impoport Pim pathlib 
from asdictass,port dataclasses imclrom data
fnal, Anyt, Optiot Dict, Lisng impore
from typi datetimmportatetime i do
frommport asyncit json
iorlogging
impmport "
i
""egrationsative intand nponents comve  React Natie withurructe app stmobilte ion
Complecatliing App Tradbile MoReact Native"""
