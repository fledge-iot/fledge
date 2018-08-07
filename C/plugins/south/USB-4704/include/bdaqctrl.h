#if defined(__cplusplus) && !defined(_BDAQ_NO_NAMESPACE) && !defined(_BDAQ_C_INTERFACE)
#  ifndef BEGIN_NAMEAPCE_AUTOMATION_BDAQ
#     define BEGIN_NAMEAPCE_AUTOMATION_BDAQ namespace Automation { namespace BDaq {
#     define END_NAMEAPCE_AUTOMATION_BDAQ  } /*BDaq*/ } /*Automation*/
#  endif
#else
#  ifndef BEGIN_NAMEAPCE_AUTOMATION_BDAQ
#     define BEGIN_NAMEAPCE_AUTOMATION_BDAQ
#     define END_NAMEAPCE_AUTOMATION_BDAQ
#  endif
#endif

// **********************************************************
// Bionic DAQ types
// **********************************************************
#ifndef _BDAQ_TYPES_DEFINED
#define _BDAQ_TYPES_DEFINED

BEGIN_NAMEAPCE_AUTOMATION_BDAQ

#define MAX_DEVICE_DESC_LEN   64
#define MAX_VRG_DESC_LEN      256
#define MAX_SIG_DROP_DESC_LEN 256

#define MAX_AI_CH_COUNT       128
#define MAX_AO_CH_COUNT       128
#define MAX_DIO_PORT_COUNT    32
#define MAX_CNTR_CH_COUNT     8

typedef signed char    int8;
typedef signed short   int16;

typedef unsigned char  uint8;
typedef unsigned short uint16;

#if defined(_WIN32) || defined(WIN32)
#  define BDAQCALL       WINAPI
#  ifndef _WIN64
      typedef signed   int  int32;
      typedef unsigned int  uint32;
#  else
      typedef signed   long int32;
      typedef unsigned long uint32;
#  endif
   typedef signed __int64   int64;
   typedef unsigned __int64 uint64;
#else
#  define BDAQCALL
   typedef signed int         int32;
   typedef unsigned int       uint32;
   typedef signed long long   int64;
   typedef unsigned long long uint64;
   typedef void *             HANDLE;
#endif

typedef enum tagTerminalBoard {
   WiringBoard = 0,
   PCLD8710,
   PCLD789,
   PCLD8115,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
    BoardUnknown = 0xffffffff,
} TerminalBoard;

typedef enum tagModuleType {
   DaqGroup = 1,
   DaqDevice,
   DaqAi,
   DaqAo,
   DaqDio,
   DaqCounter,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   DaqAny = 0xffffffff,
} ModuleType;

typedef enum tagAccessMode {
   ModeRead = 0,
   ModeWrite,
   ModeWriteWithReset,
   ModeWriteShared,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   ModeUnknown = 0xffffffff,
} AccessMode;

typedef enum Depository {
   DepositoryNone = 0,
   DepositoryOnSystem,
   DepositoryOnDevice,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   DepositoryUnknown = 0xffffffff,
} Depository;

typedef enum tagMathIntervalType {
   /* Right boundary definition, define the maximum value state, use the bit 0,1 */
   RightOpenSet        = 0x0,   /* No maximum value limitation.  */
   RightClosedBoundary = 0x1,   /* The maximum value is included. */
   RightOpenBoundary   = 0x2,   /* The maximum value is not included. */

   /* Left boundary definition, define the minimum value state, used the bit 2, 3 */
   LeftOpenSet        = 0x0,   /* No minimum value limitation. */
   LeftClosedBoundary = 0x4,   /* The minimum value is included. */
   LeftOpenBoundary   = 0x8,   /* The minimum value is not included */

   /* The signality expression */
   Boundless          = 0x0,   /* Boundless set. (LeftOpenSet | RightOpenSet) */

   /* The combination notation */
   LOSROS = 0x0,    /* (LeftOpenSet | RightOpenSet), algebra notation: (un-limit, max) */
   LOSRCB = 0x1,    /* (LeftOpenSet | RightClosedBoundary), algebra notation: (un-limit, max ] */
   LOSROB = 0x2,    /* (LeftOpenSet | RightOpenBoundary), algebra notation: (un-limit, max) */

   LCBROS = 0x4,    /* (LeftClosedBoundary | RightOpenSet), algebra notation: [min, un-limit) */
   LCBRCB = 0x5,    /* (LeftClosedBoundary | RightClosedBoundary), algebra notation: [ min, right ] */
   LCBROB = 0x6,    /* (LeftClosedBoundary | RightOpenBoundary), algebra notation: [ min, right) */

   LOBROS = 0x8,    /* (LeftOpenBoundary | RightOpenSet), algebra notation: (min, un-limit) */
   LOBRCB = 0x9,    /* (LeftOpenBoundary | RightClosedBoundary), algebra notation: (min, right ] */
   LOBROB = 0xA,    /* (LeftOpenBoundary | RightOpenBoundary), algebra notation: (min, right) */

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   IntervalUnknown = 0xffffffff,
} MathIntervalType;

typedef struct tagMathInterval {
   int32  Type; 
   double Min;
   double Max;
} MathInterval, * PMathInterval;

typedef enum tagAiChannelType {
   AllSingleEnded = 0,
   AllDifferential,
   AllSeDiffAdj,
   MixedSeDiffAdj,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   ChannelUnknown = 0xffffffff,
} AiChannelType;

typedef enum AiSignalType {
   SingleEnded = 0,
   Differential,
   PseudoDifferential,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   AiSignalUnknown = 0xffffffff,
} AiSignalType;

typedef enum tagFilterType {
   FilterNone = 0,
   LowPass,
   HighPass,
   BandPass,
   BandStop,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   FilterUnknown = 0xffffffff,
} FilterType;

typedef enum tagCouplingType {
   DCCoupling = 0,
   ACCoupling,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   CouplingUnknown = 0xffffffff,
} CouplingType;

typedef enum tagImpedanceType  {
   Ipd1Momh = 0,
   Ipd50omh,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   ImpedanceUnknown = 0xffffffff,
} ImpedanceType;

typedef enum tagIepeType  {
   IEPENone = 0,
   IEPE4mA = 1,
   IEPE10mA = 2,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   IepeUnknown = 0xffffffff,
} IepeType;

typedef enum tagDioPortType {
   PortDi = 0,        // the port number references to a DI port
   PortDo,            // the port number references to a DO port
   PortDio,           // the port number references to a DI port and a DO port
   Port8255A,         // the port number references to a PPI port A mode DIO port.
   Port8255C,         // the port number references to a PPI port C mode DIO port.
   PortIndvdlDio,     // the port number references to a port whose each channel can be configured as in or out.

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   PortUnknown = 0xffffffff,
} DioPortType;

typedef enum tagDioPortDir {
   Input   = 0x00,
   LoutHin = 0x0F,
   LinHout = 0xF0,
   Output  = 0xFF,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   DirUnknown = 0xffffffff,
} DioPortDir;

typedef enum tagDiOpenState {
   pullHighAllPort = 0x00,
   pullLowAllPort = 0x11,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   OpenStateUnknown = 0xffffffff,
} DiOpenState;

typedef enum tagSamplingMethod {
   EqualTimeSwitch = 0,
   Simultaneous,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   SamplingUnknown = 0xffffffff,
} SamplingMethod;

typedef enum tagTemperatureDegree {
   Celsius = 0,
   Fahrenheit,
   Rankine,
   Kelvin,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   DegreeUnknown = 0xffffffff,
} TemperatureDegree;

typedef enum tagBurnoutRetType {
   Current = 0,
   ParticularValue,
   UpLimit,
   LowLimit,
   LastCorrectValue,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   ReturnUnknown = 0xffffffff,
} BurnoutRetType;

typedef enum tagValueUnit {
   Kilovolt,      /* KV */
   Volt,          /* V  */
   Millivolt,     /* mV */
   Microvolt,     /* uV */
   Kiloampere,    /* KA */
   Ampere,        /* A  */
   Milliampere,   /* mA */
   Microampere,   /* uA */
   CelsiusUnit,   /* Celsius */

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   UnitUnknown = 0xffffffff,
} ValueUnit;

typedef enum tagValueRange {
   V_Neg15To15 = 0,        /* +/- 15 V  */
   V_Neg10To10,            /* +/- 10 V  */
   V_Neg5To5,              /* +/- 5 V */
   V_Neg2pt5To2pt5,        /* +/- 2.5 V */
   V_Neg1pt25To1pt25,      /* +/- 1.25 V */
   V_Neg1To1,              /* +/- 1 V */

   V_0To15,                /* 0~15 V  */
   V_0To10,                /* 0~10 V  */
   V_0To5,                 /* 0~5 V */
   V_0To2pt5,              /* 0~2.5 V */
   V_0To1pt25,             /* 0~1.25 V */
   V_0To1,                 /* 0~1 V */

   mV_Neg625To625,         /* +/- 625mV */
   mV_Neg500To500,         /* +/- 500 mV */
   mV_Neg312pt5To312pt5,   /* +/- 312.5 mV */
   mV_Neg200To200,         /* +/- 200 mV */
   mV_Neg150To150,         /* +/- 150 mV */
   mV_Neg100To100,         /* +/- 100 mV */
   mV_Neg50To50,           /* +/- 50 mV */
   mV_Neg30To30,           /* +/- 30 mV */
   mV_Neg20To20,           /* +/- 20 mV */
   mV_Neg15To15,           /* +/- 15 mV  */
   mV_Neg10To10,           /* +/- 10 mV */
   mV_Neg5To5,             /* +/- 5 mV */

   mV_0To625,              /* 0 ~ 625 mV */
   mV_0To500,              /* 0 ~ 500 mV */
   mV_0To150,              /* 0 ~ 150 mV */
   mV_0To100,              /* 0 ~ 100 mV */
   mV_0To50,               /* 0 ~ 50 mV */
   mV_0To20,               /* 0 ~ 20 mV */
   mV_0To15,               /* 0 ~ 15 mV */
   mV_0To10,               /* 0 ~ 10 mV */

   mA_Neg20To20,           /* +/- 20mA */
   mA_0To20,               /* 0 ~ 20 mA */
   mA_4To20,               /* 4 ~ 20 mA */
   mA_0To24,               /* 0 ~ 24 mA */

   /* For USB4702_4704 */
   V_Neg2To2,              /* +/- 2 V */
   V_Neg4To4,              /* +/- 4 V */
   V_Neg20To20,            /* +/- 20 V */

   Jtype_0To760C = 0x8000, /* T/C J type 0~760 'C */
   Ktype_0To1370C,         /* T/C K type 0~1370 'C */
   Ttype_Neg100To400C,     /* T/C T type -100~400 'C */
   Etype_0To1000C,         /* T/C E type 0~1000 'C */
   Rtype_500To1750C,       /* T/C R type 500~1750 'C */
   Stype_500To1750C,       /* T/C S type 500~1750 'C */
   Btype_500To1800C,       /* T/C B type 500~1800 'C */

   Pt392_Neg50To150,       /* Pt392 -50~150 'C  */
   Pt385_Neg200To200,      /* Pt385 -200~200 'C */
   Pt385_0To400,           /* Pt385 0~400 'C */
   Pt385_Neg50To150,       /* Pt385 -50~150 'C */
   Pt385_Neg100To100,      /* Pt385 -100~100 'C */
   Pt385_0To100,           /* Pt385 0~100 'C  */
   Pt385_0To200,           /* Pt385 0~200 'C */
   Pt385_0To600,           /* Pt385 0~600 'C */
   Pt392_Neg100To100,      /* Pt392 -100~100 'C  */
   Pt392_0To100,           /* Pt392 0~100 'C */
   Pt392_0To200,           /* Pt392 0~200 'C */
   Pt392_0To600,           /* Pt392 0~600 'C */
   Pt392_0To400,           /* Pt392 0~400 'C */
   Pt392_Neg200To200,      /* Pt392 -200~200 'C  */
   Pt1000_Neg40To160,      /* Pt1000 -40~160 'C  */

   Balcon500_Neg30To120,   /* Balcon500 -30~120 'C  */

   Ni518_Neg80To100,       /* Ni518 -80~100 'C */
   Ni518_0To100,           /* Ni518 0~100 'C */
   Ni508_0To100,           /* Ni508 0~100 'C */
   Ni508_Neg50To200,       /* Ni508 -50~200 'C */

   Thermistor_3K_0To100,   /* Thermistor 3K 0~100 'C */
   Thermistor_10K_0To100,  /* Thermistor 10K 0~100 'C */

   Jtype_Neg210To1200C,    /* T/C J type -210~1200 'C */
   Ktype_Neg270To1372C,    /* T/C K type -270~1372 'C */
   Ttype_Neg270To400C,     /* T/C T type -270~400 'C */
   Etype_Neg270To1000C,    /* T/C E type -270~1000 'C */
   Rtype_Neg50To1768C,     /* T/C R type -50~1768 'C */
   Stype_Neg50To1768C,     /* T/C S type -50~1768 'C */
   Btype_40To1820C,        /* T/C B type 40~1820 'C */

   Jtype_Neg210To870C,     /* T/C J type -210~870 'C */
   Rtype_0To1768C,         /* T/C R type 0~1768 'C */
   Stype_0To1768C,         /* T/C S type 0~1768 'C */
   Ttype_Neg20To135C,      /* T/C T type -20~135 'C */

   /* 0xC000 ~ 0xF000 : user customized value range type */
   UserCustomizedVrgStart = 0xC000,
   UserCustomizedVrgEnd = 0xF000,

   /* AO external reference type */
   V_ExternalRefBipolar = 0xF001,  /* External reference voltage unipolar */
   V_ExternalRefUnipolar = 0xF002, /* External reference voltage bipolar */

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   V_OMIT = 0xffffffff,            /* Unknown when get, ignored when set */
} ValueRange;

typedef enum tagSignalPolarity {
   Negative = 0,
   Positive,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   PolarityUnknown = 0xffffffff,
} SignalPolarity;

typedef enum tagSignalCountingType {
   CountingNone = 0,
   DownCount,      /* counter value decreases on each clock */
   UpCount,        /* counter value increases on each clock */
   PulseDirection, /* counting direction is determined by two signals, one is clock, the other is direction signal */
   TwoPulse,       /* counting direction is determined by two signals, one is up-counting signal, the other is down-counting signal */
   AbPhaseX1,      /* AB phase, 1x rate up/down counting */
   AbPhaseX2,      /* AB phase, 2x rate up/down counting */
   AbPhaseX4,      /* AB phase, 4x rate up/down counting */

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   CountingUnknown = 0xffffffff,
} CountingType;

/*for compatible*/ 
typedef CountingType SignalCountingType; 

typedef enum tagOutSignalType{
   SignalOutNone = 0,  /* no output or output is 'disabled' */
   ChipDefined,        /* hardware chip defined */
   NegChipDefined,     /* hardware chip defined, negative logical */
   PositivePulse,      /* a low-to-high pulse */
   NegativePulse,      /* a high-to-low pulse */
   ToggledFromLow,     /* the level toggled from low to high */
   ToggledFromHigh,    /* the level toggled from high to low */

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   OutSignalUnknown = 0xffffffff,
} OutSignalType;

typedef enum tagCounterCapability {
   Primary = 1,
   InstantEventCount,
   OneShot,
   TimerPulse,
   InstantFreqMeter,
   InstantPwmIn,
   InstantPwmOut,
   UpDownCount,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   CapabilityUnknown = 0xffffffff,
} CounterCapability;

typedef enum tagCounterOperationMode {
   C8254_M0 = 0, /*8254 mode 0, interrupt on terminal count */
   C8254_M1,     /*8254 mode 1, hardware retriggerable one-shot */
   C8254_M2,     /*8254 mode 2, rate generator */
   C8254_M3,     /*8254 mode 3, square save mode */
   C8254_M4,     /*8254 mode 4, software triggered strobe */
   C8254_M5,     /*8254 mode 5, hardware triggered strobe */

   C1780_MA,    /* Mode A level & pulse out, Software-Triggered without Hardware Gating */
   C1780_MB,    /* Mode B level & pulse out, Software-Triggered with Level Gating, = 8254_M0 */
   C1780_MC,    /* Mode C level & pulse out, Hardware-triggered strobe level */
   C1780_MD,    /* Mode D level & Pulse out, Rate generate with no hardware gating */
   C1780_ME,    /* Mode E level & pulse out, Rate generator with level Gating */
   C1780_MF,    /* Mode F level & pulse out, Non-retriggerable One-shot (Pulse type = 8254_M1) */
   C1780_MG,    /* Mode G level & pulse out, Software-triggered delayed pulse one-shot */
   C1780_MH,    /* Mode H level & pulse out, Software-triggered delayed pulse one-shot with hardware gating */
   C1780_MI,    /* Mode I level & pulse out, Hardware-triggered delay pulse strobe */
   C1780_MJ,    /* Mode J level & pulse out, Variable Duty Cycle Rate Generator with No Hardware Gating */
   C1780_MK,    /* Mode K level & pulse out, Variable Duty Cycle Rate Generator with Level Gating */
   C1780_ML,    /* Mode L level & pulse out, Hardware-Triggered Delayed Pulse One-Shot */
   C1780_MO,    /* Mode O level & pulse out, Hardware-Triggered Strobe with Edge Disarm */
   C1780_MR,    /* Mode R level & pulse out, Non-Retriggerbale One-Shot with Edge Disarm */
   C1780_MU,    /* Mode U level & pulse out, Hardware-Triggered Delayed Pulse Strobe with Edge Disarm */
   C1780_MX,    /* Mode X level & pulse out, Hardware-Triggered Delayed Pulse One-Shot with Edge Disarm */

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   OpModeUnknown = 0xffffffff,
} CounterOperationMode;

typedef enum tagCounterValueRegister {
   CntLoad,
   CntPreset = CntLoad,
   CntHold,
   CntOverCompare,
   CntUnderCompare,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
  RegisterUnknown = 0xffffffff,
} CounterValueRegister;

typedef enum tagCounterCascadeGroup {
   GroupNone = 0,    /* no cascade*/
   Cnt0Cnt1,         /* Counter 0 as first, counter 1 as second. */
   Cnt2Cnt3,         /* Counter 2 as first, counter 3 as second */
   Cnt4Cnt5,         /* Counter 4 as first, counter 5 as second */
   Cnt6Cnt7,         /* Counter 6 as first, counter 7 as second */

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   CascadeUnknown = 0xffffffff,
} CounterCascadeGroup;

typedef enum tagFreqMeasureMethod {
   AutoAdaptive = 0,          /* Intelligently select the measurement method according to the input signal. */
   CountingPulseBySysTime,    /* Using system timing clock to calculate the frequency */
   CountingPulseByDevTime,    /* Using the device timing clock to calculate the frequency */
   PeriodInverse,             /* Calculate the frequency from the period of the signal */

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   MethodUnknown = 0xffffffff,
} FreqMeasureMethod;

typedef enum tagActiveSignal {
   ActiveNone = 0,
   RisingEdge,
   FallingEdge,
   BothEdge,
   HighLevel,
   LowLevel,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   ActSignalUnknown = 0xffffffff,
} ActiveSignal;

typedef enum tagTriggerAction {
   ActionNone = 0,   /* No action to take even if the trigger condition is satisfied */
   DelayToStart,     /* Begin to start after the specified time is elapsed if the trigger condition is satisfied */
   DelayToStop,      /* Stop execution after the specified time is elapsed if the trigger condition is satisfied */
   Mark,             /* Generate a mark data*/

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   ActionUnknown = 0xffffffff,
} TriggerAction;

typedef enum tagSignalPosition {
   InternalSig = 0,
   OnConnector,
   OnAmsi,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   PositionUnknown = 0xffffffff,
} SignalPosition;

typedef enum tagSignalDrop {
   SignalNone = 0,          /* No connection */

   /*Internal signal connector*/
   SigInternalClock,        /* Device built-in clock, If the device has several built-in clock, this represent the highest freq one. */
   SigInternal1KHz,         /* Device built-in clock, 1KHz */
   SigInternal10KHz,        /* Device built-in clock, 10KHz */
   SigInternal100KHz,       /* Device built-in clock, 100KHz */
   SigInternal1MHz,         /* Device built-in clock, 1MHz */
   SigInternal10MHz,        /* Device built-in clock, 10MHz */
   SigInternal20MHz,        /* Device built-in clock, 20MHz */
   SigInternal30MHz,        /* Device built-in clock, 30MHz */
   SigInternal40MHz,        /* Device built-in clock, 40MHz */
   SigInternal50MHz,        /* Device built-in clock, 50MHz */
   SigInternal60MHz,        /* Device built-in clock, 60MHz */

   SigDiPatternMatch,       /* When DI pattern match occurred */
   SigDiStatusChange,       /* When DI status change occurred */

   /*Function pin on connector*/
   SigExtAnaClock,          /* Analog clock pin of connector */
   SigExtAnaScanClock,      /* scan clock pin of connector */
   SigExtAnaTrigger,        /* external analog trigger pin of connector */
   SigExtAnaTrigger0 = SigExtAnaTrigger, /* external analog trigger pin of connector 0*/
   SigExtDigClock,          /* digital clock pin of connector */
   SigExtDigTrigger0,       /* external digital trigger 0 pin(or DI start trigger pin) of connector */
   SigExtDigTrigger1,       /* external digital trigger 1 pin(or DI stop trigger pin) of connector  */
   SigExtDigTrigger2,       /* external digital trigger 2 pin(or DO start trigger pin) of connector */
   SigExtDigTrigger3,       /* external digital trigger 3 pin(or DO stop trigger pin) of connector  */
   SigCHFrzDo,              /* Channel freeze DO ports pin */

   /*Signal source or target on the connector*/
   /*AI channel pins*/
   SigAi0,  SigAi1,  SigAi2,  SigAi3,  SigAi4,  SigAi5,  SigAi6,  SigAi7, 
   SigAi8,  SigAi9,  SigAi10, SigAi11, SigAi12, SigAi13, SigAi14, SigAi15,
   SigAi16, SigAi17, SigAi18, SigAi19, SigAi20, SigAi21, SigAi22, SigAi23,
   SigAi24, SigAi25, SigAi26, SigAi27, SigAi28, SigAi29, SigAi30, SigAi31, 
   SigAi32, SigAi33, SigAi34, SigAi35, SigAi36, SigAi37, SigAi38, SigAi39,
   SigAi40, SigAi41, SigAi42, SigAi43, SigAi44, SigAi45, SigAi46, SigAi47,
   SigAi48, SigAi49, SigAi50, SigAi51, SigAi52, SigAi53, SigAi54, SigAi55, 
   SigAi56, SigAi57, SigAi58, SigAi59, SigAi60, SigAi61, SigAi62, SigAi63,

   /*AO channel pins*/
   SigAo0,  SigAo1,  SigAo2,  SigAo3,  SigAo4,  SigAo5,  SigAo6,  SigAo7,
   SigAo8,  SigAo9,  SigAo10, SigAo11, SigAo12, SigAo13, SigAo14, SigAo15,
   SigAo16, SigAo17, SigAo18, SigAo19, SigAo20, SigAo21, SigAo22, SigAo23,
   SigAo24, SigAo25, SigAo26, SigAo27, SigAo28, SigAo29, SigAo30, SigAo31,

   /*DI pins*/
   SigDi0,   SigDi1,   SigDi2,   SigDi3,   SigDi4,   SigDi5,   SigDi6,   SigDi7,
   SigDi8,   SigDi9,   SigDi10,  SigDi11,  SigDi12,  SigDi13,  SigDi14,  SigDi15,
   SigDi16,  SigDi17,  SigDi18,  SigDi19,  SigDi20,  SigDi21,  SigDi22,  SigDi23,
   SigDi24,  SigDi25,  SigDi26,  SigDi27,  SigDi28,  SigDi29,  SigDi30,  SigDi31,
   SigDi32,  SigDi33,  SigDi34,  SigDi35,  SigDi36,  SigDi37,  SigDi38,  SigDi39,
   SigDi40,  SigDi41,  SigDi42,  SigDi43,  SigDi44,  SigDi45,  SigDi46,  SigDi47,
   SigDi48,  SigDi49,  SigDi50,  SigDi51,  SigDi52,  SigDi53,  SigDi54,  SigDi55,
   SigDi56,  SigDi57,  SigDi58,  SigDi59,  SigDi60,  SigDi61,  SigDi62,  SigDi63,
   SigDi64,  SigDi65,  SigDi66,  SigDi67,  SigDi68,  SigDi69,  SigDi70,  SigDi71,
   SigDi72,  SigDi73,  SigDi74,  SigDi75,  SigDi76,  SigDi77,  SigDi78,  SigDi79,
   SigDi80,  SigDi81,  SigDi82,  SigDi83,  SigDi84,  SigDi85,  SigDi86,  SigDi87,
   SigDi88,  SigDi89,  SigDi90,  SigDi91,  SigDi92,  SigDi93,  SigDi94,  SigDi95,
   SigDi96,  SigDi97,  SigDi98,  SigDi99,  SigDi100, SigDi101, SigDi102, SigDi103,
   SigDi104, SigDi105, SigDi106, SigDi107, SigDi108, SigDi109, SigDi110, SigDi111,
   SigDi112, SigDi113, SigDi114, SigDi115, SigDi116, SigDi117, SigDi118, SigDi119,
   SigDi120, SigDi121, SigDi122, SigDi123, SigDi124, SigDi125, SigDi126, SigDi127,
   SigDi128, SigDi129, SigDi130, SigDi131, SigDi132, SigDi133, SigDi134, SigDi135,
   SigDi136, SigDi137, SigDi138, SigDi139, SigDi140, SigDi141, SigDi142, SigDi143,
   SigDi144, SigDi145, SigDi146, SigDi147, SigDi148, SigDi149, SigDi150, SigDi151,
   SigDi152, SigDi153, SigDi154, SigDi155, SigDi156, SigDi157, SigDi158, SigDi159,
   SigDi160, SigDi161, SigDi162, SigDi163, SigDi164, SigDi165, SigDi166, SigDi167,
   SigDi168, SigDi169, SigDi170, SigDi171, SigDi172, SigDi173, SigDi174, SigDi175,
   SigDi176, SigDi177, SigDi178, SigDi179, SigDi180, SigDi181, SigDi182, SigDi183,
   SigDi184, SigDi185, SigDi186, SigDi187, SigDi188, SigDi189, SigDi190, SigDi191,
   SigDi192, SigDi193, SigDi194, SigDi195, SigDi196, SigDi197, SigDi198, SigDi199,
   SigDi200, SigDi201, SigDi202, SigDi203, SigDi204, SigDi205, SigDi206, SigDi207,
   SigDi208, SigDi209, SigDi210, SigDi211, SigDi212, SigDi213, SigDi214, SigDi215,
   SigDi216, SigDi217, SigDi218, SigDi219, SigDi220, SigDi221, SigDi222, SigDi223,
   SigDi224, SigDi225, SigDi226, SigDi227, SigDi228, SigDi229, SigDi230, SigDi231,
   SigDi232, SigDi233, SigDi234, SigDi235, SigDi236, SigDi237, SigDi238, SigDi239,
   SigDi240, SigDi241, SigDi242, SigDi243, SigDi244, SigDi245, SigDi246, SigDi247,
   SigDi248, SigDi249, SigDi250, SigDi251, SigDi252, SigDi253, SigDi254, SigDi255,

   /*DIO pins*/
   SigDio0,   SigDio1,   SigDio2,   SigDio3,   SigDio4,   SigDio5,   SigDio6,   SigDio7,
   SigDio8,   SigDio9,   SigDio10,  SigDio11,  SigDio12,  SigDio13,  SigDio14,  SigDio15,
   SigDio16,  SigDio17,  SigDio18,  SigDio19,  SigDio20,  SigDio21,  SigDio22,  SigDio23,
   SigDio24,  SigDio25,  SigDio26,  SigDio27,  SigDio28,  SigDio29,  SigDio30,  SigDio31,
   SigDio32,  SigDio33,  SigDio34,  SigDio35,  SigDio36,  SigDio37,  SigDio38,  SigDio39,
   SigDio40,  SigDio41,  SigDio42,  SigDio43,  SigDio44,  SigDio45,  SigDio46,  SigDio47,
   SigDio48,  SigDio49,  SigDio50,  SigDio51,  SigDio52,  SigDio53,  SigDio54,  SigDio55,
   SigDio56,  SigDio57,  SigDio58,  SigDio59,  SigDio60,  SigDio61,  SigDio62,  SigDio63,
   SigDio64,  SigDio65,  SigDio66,  SigDio67,  SigDio68,  SigDio69,  SigDio70,  SigDio71,
   SigDio72,  SigDio73,  SigDio74,  SigDio75,  SigDio76,  SigDio77,  SigDio78,  SigDio79,
   SigDio80,  SigDio81,  SigDio82,  SigDio83,  SigDio84,  SigDio85,  SigDio86,  SigDio87,
   SigDio88,  SigDio89,  SigDio90,  SigDio91,  SigDio92,  SigDio93,  SigDio94,  SigDio95,
   SigDio96,  SigDio97,  SigDio98,  SigDio99,  SigDio100, SigDio101, SigDio102, SigDio103,
   SigDio104, SigDio105, SigDio106, SigDio107, SigDio108, SigDio109, SigDio110, SigDio111,
   SigDio112, SigDio113, SigDio114, SigDio115, SigDio116, SigDio117, SigDio118, SigDio119,
   SigDio120, SigDio121, SigDio122, SigDio123, SigDio124, SigDio125, SigDio126, SigDio127,
   SigDio128, SigDio129, SigDio130, SigDio131, SigDio132, SigDio133, SigDio134, SigDio135,
   SigDio136, SigDio137, SigDio138, SigDio139, SigDio140, SigDio141, SigDio142, SigDio143,
   SigDio144, SigDio145, SigDio146, SigDio147, SigDio148, SigDio149, SigDio150, SigDio151,
   SigDio152, SigDio153, SigDio154, SigDio155, SigDio156, SigDio157, SigDio158, SigDio159,
   SigDio160, SigDio161, SigDio162, SigDio163, SigDio164, SigDio165, SigDio166, SigDio167,
   SigDio168, SigDio169, SigDio170, SigDio171, SigDio172, SigDio173, SigDio174, SigDio175,
   SigDio176, SigDio177, SigDio178, SigDio179, SigDio180, SigDio181, SigDio182, SigDio183,
   SigDio184, SigDio185, SigDio186, SigDio187, SigDio188, SigDio189, SigDio190, SigDio191,
   SigDio192, SigDio193, SigDio194, SigDio195, SigDio196, SigDio197, SigDio198, SigDio199,
   SigDio200, SigDio201, SigDio202, SigDio203, SigDio204, SigDio205, SigDio206, SigDio207,
   SigDio208, SigDio209, SigDio210, SigDio211, SigDio212, SigDio213, SigDio214, SigDio215,
   SigDio216, SigDio217, SigDio218, SigDio219, SigDio220, SigDio221, SigDio222, SigDio223,
   SigDio224, SigDio225, SigDio226, SigDio227, SigDio228, SigDio229, SigDio230, SigDio231,
   SigDio232, SigDio233, SigDio234, SigDio235, SigDio236, SigDio237, SigDio238, SigDio239,
   SigDio240, SigDio241, SigDio242, SigDio243, SigDio244, SigDio245, SigDio246, SigDio247,
   SigDio248, SigDio249, SigDio250, SigDio251, SigDio252, SigDio253, SigDio254, SigDio255,

   /*Counter clock pins*/
   SigCntClk0, SigCntClk1, SigCntClk2, SigCntClk3, SigCntClk4, SigCntClk5, SigCntClk6, SigCntClk7,

   /*counter gate pins*/
   SigCntGate0, SigCntGate1, SigCntGate2, SigCntGate3, SigCntGate4, SigCntGate5, SigCntGate6, SigCntGate7,

   /*counter out pins*/
   SigCntOut0,  SigCntOut1,  SigCntOut2,  SigCntOut3,  SigCntOut4,  SigCntOut5,  SigCntOut6,  SigCntOut7,

   /*counter frequency out pins*/
   SigCntFout0, SigCntFout1, SigCntFout2, SigCntFout3, SigCntFout4, SigCntFout5, SigCntFout6, SigCntFout7,

   /*AMSI pins*/
   SigAmsiPin0,  SigAmsiPin1,  SigAmsiPin2,  SigAmsiPin3,  SigAmsiPin4,  SigAmsiPin5,  SigAmsiPin6,  SigAmsiPin7,
   SigAmsiPin8,  SigAmsiPin9,  SigAmsiPin10, SigAmsiPin11, SigAmsiPin12, SigAmsiPin13, SigAmsiPin14, SigAmsiPin15,
   SigAmsiPin16, SigAmsiPin17, SigAmsiPin18, SigAmsiPin19,

   /*new clocks*/
   SigInternal2Hz,         /* Device built-in clock, 2Hz */
   SigInternal20Hz,        /* Device built-in clock, 20Hz */
   SigInternal200Hz,       /* Device built-in clock, 200KHz */
   SigInternal2KHz,        /* Device built-in clock, 2KHz */
   SigInternal20KHz,       /* Device built-in clock, 20KHz */
   SigInternal200KHz,      /* Device built-in clock, 200KHz */
   SigInternal2MHz,        /* Device built-in clock, 2MHz */
   
   /*New Function pin on connector*/
   SigExtAnaTrigger1,      /* external analog trigger pin of connector 1 */

   /*Reference clock*/
   SigExtDigRefClock,      /* digital clock pin of connector */

   /*New Function pin on connector*/
   SigInternal100MHz,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   SigDropUnknown = 0xffffffff,
} SignalDrop;

/*
* Event Id
*/
typedef enum tagEventId {
   EvtDeviceRemoved = 0,  /* The device was removed from system */
   EvtDeviceReconnected,  /* The device is reconnected */
   EvtPropertyChanged,    /* Some properties of the device were changed */
   /*-----------------------------------------------------------------
   * AI events
   *-----------------------------------------------------------------*/
   EvtBufferedAiDataReady, 
   EvtBufferedAiOverrun,
   EvtBufferedAiCacheOverflow,
   EvtBufferedAiStopped,

   /*-----------------------------------------------------------------
   * AO event IDs
   *-----------------------------------------------------------------*/
   EvtBufferedAoDataTransmitted,
   EvtBufferedAoUnderrun,
   EvtBufferedAoCacheEmptied,
   EvtBufferedAoTransStopped,
   EvtBufferedAoStopped,

   /*-----------------------------------------------------------------
   * DIO event IDs
   *-----------------------------------------------------------------*/
   EvtDiintChannel000, EvtDiintChannel001, EvtDiintChannel002, EvtDiintChannel003,
   EvtDiintChannel004, EvtDiintChannel005, EvtDiintChannel006, EvtDiintChannel007,
   EvtDiintChannel008, EvtDiintChannel009, EvtDiintChannel010, EvtDiintChannel011,
   EvtDiintChannel012, EvtDiintChannel013, EvtDiintChannel014, EvtDiintChannel015,
   EvtDiintChannel016, EvtDiintChannel017, EvtDiintChannel018, EvtDiintChannel019,
   EvtDiintChannel020, EvtDiintChannel021, EvtDiintChannel022, EvtDiintChannel023,
   EvtDiintChannel024, EvtDiintChannel025, EvtDiintChannel026, EvtDiintChannel027,
   EvtDiintChannel028, EvtDiintChannel029, EvtDiintChannel030, EvtDiintChannel031,
   EvtDiintChannel032, EvtDiintChannel033, EvtDiintChannel034, EvtDiintChannel035,
   EvtDiintChannel036, EvtDiintChannel037, EvtDiintChannel038, EvtDiintChannel039,
   EvtDiintChannel040, EvtDiintChannel041, EvtDiintChannel042, EvtDiintChannel043,
   EvtDiintChannel044, EvtDiintChannel045, EvtDiintChannel046, EvtDiintChannel047,
   EvtDiintChannel048, EvtDiintChannel049, EvtDiintChannel050, EvtDiintChannel051,
   EvtDiintChannel052, EvtDiintChannel053, EvtDiintChannel054, EvtDiintChannel055,
   EvtDiintChannel056, EvtDiintChannel057, EvtDiintChannel058, EvtDiintChannel059,
   EvtDiintChannel060, EvtDiintChannel061, EvtDiintChannel062, EvtDiintChannel063,
   EvtDiintChannel064, EvtDiintChannel065, EvtDiintChannel066, EvtDiintChannel067,
   EvtDiintChannel068, EvtDiintChannel069, EvtDiintChannel070, EvtDiintChannel071,
   EvtDiintChannel072, EvtDiintChannel073, EvtDiintChannel074, EvtDiintChannel075,
   EvtDiintChannel076, EvtDiintChannel077, EvtDiintChannel078, EvtDiintChannel079,
   EvtDiintChannel080, EvtDiintChannel081, EvtDiintChannel082, EvtDiintChannel083,
   EvtDiintChannel084, EvtDiintChannel085, EvtDiintChannel086, EvtDiintChannel087,
   EvtDiintChannel088, EvtDiintChannel089, EvtDiintChannel090, EvtDiintChannel091,
   EvtDiintChannel092, EvtDiintChannel093, EvtDiintChannel094, EvtDiintChannel095,
   EvtDiintChannel096, EvtDiintChannel097, EvtDiintChannel098, EvtDiintChannel099,
   EvtDiintChannel100, EvtDiintChannel101, EvtDiintChannel102, EvtDiintChannel103,
   EvtDiintChannel104, EvtDiintChannel105, EvtDiintChannel106, EvtDiintChannel107,
   EvtDiintChannel108, EvtDiintChannel109, EvtDiintChannel110, EvtDiintChannel111,
   EvtDiintChannel112, EvtDiintChannel113, EvtDiintChannel114, EvtDiintChannel115,
   EvtDiintChannel116, EvtDiintChannel117, EvtDiintChannel118, EvtDiintChannel119,
   EvtDiintChannel120, EvtDiintChannel121, EvtDiintChannel122, EvtDiintChannel123,
   EvtDiintChannel124, EvtDiintChannel125, EvtDiintChannel126, EvtDiintChannel127,
   EvtDiintChannel128, EvtDiintChannel129, EvtDiintChannel130, EvtDiintChannel131,
   EvtDiintChannel132, EvtDiintChannel133, EvtDiintChannel134, EvtDiintChannel135,
   EvtDiintChannel136, EvtDiintChannel137, EvtDiintChannel138, EvtDiintChannel139,
   EvtDiintChannel140, EvtDiintChannel141, EvtDiintChannel142, EvtDiintChannel143,
   EvtDiintChannel144, EvtDiintChannel145, EvtDiintChannel146, EvtDiintChannel147,
   EvtDiintChannel148, EvtDiintChannel149, EvtDiintChannel150, EvtDiintChannel151,
   EvtDiintChannel152, EvtDiintChannel153, EvtDiintChannel154, EvtDiintChannel155,
   EvtDiintChannel156, EvtDiintChannel157, EvtDiintChannel158, EvtDiintChannel159,
   EvtDiintChannel160, EvtDiintChannel161, EvtDiintChannel162, EvtDiintChannel163,
   EvtDiintChannel164, EvtDiintChannel165, EvtDiintChannel166, EvtDiintChannel167,
   EvtDiintChannel168, EvtDiintChannel169, EvtDiintChannel170, EvtDiintChannel171,
   EvtDiintChannel172, EvtDiintChannel173, EvtDiintChannel174, EvtDiintChannel175,
   EvtDiintChannel176, EvtDiintChannel177, EvtDiintChannel178, EvtDiintChannel179,
   EvtDiintChannel180, EvtDiintChannel181, EvtDiintChannel182, EvtDiintChannel183,
   EvtDiintChannel184, EvtDiintChannel185, EvtDiintChannel186, EvtDiintChannel187,
   EvtDiintChannel188, EvtDiintChannel189, EvtDiintChannel190, EvtDiintChannel191,
   EvtDiintChannel192, EvtDiintChannel193, EvtDiintChannel194, EvtDiintChannel195,
   EvtDiintChannel196, EvtDiintChannel197, EvtDiintChannel198, EvtDiintChannel199,
   EvtDiintChannel200, EvtDiintChannel201, EvtDiintChannel202, EvtDiintChannel203,
   EvtDiintChannel204, EvtDiintChannel205, EvtDiintChannel206, EvtDiintChannel207,
   EvtDiintChannel208, EvtDiintChannel209, EvtDiintChannel210, EvtDiintChannel211,
   EvtDiintChannel212, EvtDiintChannel213, EvtDiintChannel214, EvtDiintChannel215,
   EvtDiintChannel216, EvtDiintChannel217, EvtDiintChannel218, EvtDiintChannel219,
   EvtDiintChannel220, EvtDiintChannel221, EvtDiintChannel222, EvtDiintChannel223,
   EvtDiintChannel224, EvtDiintChannel225, EvtDiintChannel226, EvtDiintChannel227,
   EvtDiintChannel228, EvtDiintChannel229, EvtDiintChannel230, EvtDiintChannel231,
   EvtDiintChannel232, EvtDiintChannel233, EvtDiintChannel234, EvtDiintChannel235,
   EvtDiintChannel236, EvtDiintChannel237, EvtDiintChannel238, EvtDiintChannel239,
   EvtDiintChannel240, EvtDiintChannel241, EvtDiintChannel242, EvtDiintChannel243,
   EvtDiintChannel244, EvtDiintChannel245, EvtDiintChannel246, EvtDiintChannel247,
   EvtDiintChannel248, EvtDiintChannel249, EvtDiintChannel250, EvtDiintChannel251,
   EvtDiintChannel252, EvtDiintChannel253, EvtDiintChannel254, EvtDiintChannel255,

   EvtDiCosintPort000, EvtDiCosintPort001, EvtDiCosintPort002, EvtDiCosintPort003,
   EvtDiCosintPort004, EvtDiCosintPort005, EvtDiCosintPort006, EvtDiCosintPort007,
   EvtDiCosintPort008, EvtDiCosintPort009, EvtDiCosintPort010, EvtDiCosintPort011,
   EvtDiCosintPort012, EvtDiCosintPort013, EvtDiCosintPort014, EvtDiCosintPort015,
   EvtDiCosintPort016, EvtDiCosintPort017, EvtDiCosintPort018, EvtDiCosintPort019,
   EvtDiCosintPort020, EvtDiCosintPort021, EvtDiCosintPort022, EvtDiCosintPort023,
   EvtDiCosintPort024, EvtDiCosintPort025, EvtDiCosintPort026, EvtDiCosintPort027,
   EvtDiCosintPort028, EvtDiCosintPort029, EvtDiCosintPort030, EvtDiCosintPort031,

   EvtDiPmintPort000,  EvtDiPmintPort001,  EvtDiPmintPort002,  EvtDiPmintPort003,
   EvtDiPmintPort004,  EvtDiPmintPort005,  EvtDiPmintPort006,  EvtDiPmintPort007,
   EvtDiPmintPort008,  EvtDiPmintPort009,  EvtDiPmintPort010,  EvtDiPmintPort011,
   EvtDiPmintPort012,  EvtDiPmintPort013,  EvtDiPmintPort014,  EvtDiPmintPort015,
   EvtDiPmintPort016,  EvtDiPmintPort017,  EvtDiPmintPort018,  EvtDiPmintPort019,
   EvtDiPmintPort020,  EvtDiPmintPort021,  EvtDiPmintPort022,  EvtDiPmintPort023,
   EvtDiPmintPort024,  EvtDiPmintPort025,  EvtDiPmintPort026,  EvtDiPmintPort027,
   EvtDiPmintPort028,  EvtDiPmintPort029,  EvtDiPmintPort030,  EvtDiPmintPort031,

   EvtBufferedDiDataReady,
   EvtBufferedDiOverrun,
   EvtBufferedDiCacheOverflow,
   EvtBufferedDiStopped,

   EvtBufferedDoDataTransmitted,
   EvtBufferedDoUnderrun,
   EvtBufferedDoCacheEmptied,
   EvtBufferedDoTransStopped,
   EvtBufferedDoStopped,

   EvtReflectWdtOccured,
   /*-----------------------------------------------------------------
   * Counter/Timer event IDs
   *-----------------------------------------------------------------*/
   EvtCntTerminalCount0, EvtCntTerminalCount1, EvtCntTerminalCount2, EvtCntTerminalCount3,
   EvtCntTerminalCount4, EvtCntTerminalCount5, EvtCntTerminalCount6, EvtCntTerminalCount7,

   EvtCntOverCompare0,   EvtCntOverCompare1,   EvtCntOverCompare2,   EvtCntOverCompare3,
   EvtCntOverCompare4,   EvtCntOverCompare5,   EvtCntOverCompare6,   EvtCntOverCompare7,

   EvtCntUnderCompare0,  EvtCntUnderCompare1,  EvtCntUnderCompare2,  EvtCntUnderCompare3,
   EvtCntUnderCompare4,  EvtCntUnderCompare5,  EvtCntUnderCompare6,  EvtCntUnderCompare7,

   EvtCntEcOverCompare0, EvtCntEcOverCompare1, EvtCntEcOverCompare2, EvtCntEcOverCompare3,
   EvtCntEcOverCompare4, EvtCntEcOverCompare5, EvtCntEcOverCompare6, EvtCntEcOverCompare7,

   EvtCntEcUnderCompare0, EvtCntEcUnderCompare1, EvtCntEcUnderCompare2, EvtCntEcUnderCompare3,
   EvtCntEcUnderCompare4, EvtCntEcUnderCompare5, EvtCntEcUnderCompare6, EvtCntEcUnderCompare7,

   EvtCntOneShot0,       EvtCntOneShot1,       EvtCntOneShot2,       EvtCntOneShot3,
   EvtCntOneShot4,       EvtCntOneShot5,       EvtCntOneShot6,       EvtCntOneShot7,

   EvtCntTimer0,         EvtCntTimer1,         EvtCntTimer2,         EvtCntTimer3,
   EvtCntTimer4,         EvtCntTimer5,         EvtCntTimer6,         EvtCntTimer7,

   EvtCntPwmInOverflow0, EvtCntPwmInOverflow1, EvtCntPwmInOverflow2, EvtCntPwmInOverflow3,
   EvtCntPwmInOverflow4, EvtCntPwmInOverflow5, EvtCntPwmInOverflow6, EvtCntPwmInOverflow7,

   EvtUdIndex0, EvtUdIndex1, EvtUdIndex2, EvtUdIndex3,
   EvtUdIndex4, EvtUdIndex5, EvtUdIndex6, EvtUdIndex7,

   EvtCntPatternMatch0, EvtCntPatternMatch1, EvtCntPatternMatch2, EvtCntPatternMatch3,
   EvtCntPatternMatch4, EvtCntPatternMatch5, EvtCntPatternMatch6, EvtCntPatternMatch7,

   EvtCntCompareTableEnd0, EvtCntCompareTableEnd1, EvtCntCompareTableEnd2, EvtCntCompareTableEnd3,
   EvtCntCompareTableEnd4, EvtCntCompareTableEnd5, EvtCntCompareTableEnd6, EvtCntCompareTableEnd7,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.1: new event of AI
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   EvtBufferedAiBurnOut,
   EvtBufferedAiTimeStampOverrun,
   EvtBufferedAiTimeStampCacheOverflow,
   EvtBufferedAiMarkOverrun,
   EvtBufferedAiConvStopped,

   /*----------------------------------------------------------------------*/
   /*Dummy ID, to ensure the type is compiled as 'int' by various compiler */
   EventUnknown = 0xffffffff,
} EventId ;

/*
* Property Attribute and Id
*/
typedef enum tagPropertyAttribute {
   ReadOnly = 0,
   Writable = 1,
   Modal = 0,
   Nature = 2,
} PropertyAttribute;

typedef enum tagPropertyId {
   /*-----------------------------------------------------------------
   * common property
   *-----------------------------------------------------------------*/
   CFG_Number,
   CFG_ComponentType,
   CFG_Description,
   CFG_Parent,
   CFG_ChildList,

   /*-----------------------------------------------------------------
   * component specified Property IDs -- group
   *-----------------------------------------------------------------*/
   CFG_DevicesNumber,
   CFG_DevicesHandle,

   /*-----------------------------------------------------------------
   * component specified Property IDs -- device
   *-----------------------------------------------------------------*/
   CFG_DeviceGroupNumber,
   CFG_DeviceProductID,
   CFG_DeviceBoardID,
   CFG_DeviceBoardVersion,
   CFG_DeviceDriverVersion,
   CFG_DeviceDllVersion,
   CFG_DeviceLocation,                       /* Reserved for later using */
   CFG_DeviceBaseAddresses,                  /* Reserved for later using */
   CFG_DeviceInterrupts,                     /* Reserved for later using */
   CFG_DeviceSupportedTerminalBoardTypes,    /* Reserved for later using */
   CFG_DeviceTerminalBoardType,              /* Reserved for later using */
   CFG_DeviceSupportedEvents,
   CFG_DeviceHotResetPreventable,            /* Reserved for later using */
   CFG_DeviceLoadingTimeInit,                /* Reserved for later using */
   CFG_DeviceWaitingForReconnect,
   CFG_DeviceWaitingForSleep,

   /*-----------------------------------------------------------------
   * component specified Property IDs -- AI, AO...
   *-----------------------------------------------------------------*/
   CFG_FeatureResolutionInBit,
   CFG_FeatureDataSize,
   CFG_FeatureDataMask,
   CFG_FeatureChannelNumberMax,
   CFG_FeatureChannelConnectionType,
   CFG_FeatureBurnDetectedReturnTypes,
   CFG_FeatureBurnoutDetectionChannels,
   CFG_FeatureOverallVrgType,
   CFG_FeatureVrgTypes,
   CFG_FeatureExtRefRange,
   CFG_FeatureExtRefAntiPolar,
   CFG_FeatureCjcChannels,
   CFG_FeatureChannelScanMethod,
   CFG_FeatureScanChannelStartBase,
   CFG_FeatureScanChannelCountBase,
   CFG_FeatureConvertClockSources,
   CFG_FeatureConvertClockRateRange,       /* Reserved for later using */
   CFG_FeatureScanClockSources,
   CFG_FeatureScanClockRateRange,         /* Reserved for later using */
   CFG_FeatureScanCountMax,               /* Reserved for later using */
   CFG_FeatureTriggersCount,
   CFG_FeatureTriggerSources,
   CFG_FeatureTriggerActions,
   CFG_FeatureTriggerDelayCountRange,
   CFG_FeatureTrigger1Sources,            /* Reserved for later using */
   CFG_FeatureTrigger1Actions,            /* Reserved for later using */
   CFG_FeatureTrigger1DelayCountRange,    /* Reserved for later using */

   CFG_ChannelCount,
   CFG_ConnectionTypeOfChannels,
   CFG_VrgTypeOfChannels,
   CFG_BurnDetectedReturnTypeOfChannels,
   CFG_BurnoutReturnValueOfChannels,
   CFG_ExtRefValueForUnipolar,         /* Reserved for later using */
   CFG_ExtRefValueForBipolar,          /* Reserved for later using */

   CFG_CjcChannel,
   CFG_CjcUpdateFrequency,             /* Reserved for later using */
   CFG_CjcValue,

   CFG_SectionDataCount,
   CFG_ConvertClockSource,
   CFG_ConvertClockRatePerChannel,
   CFG_ScanChannelStart,
   CFG_ScanChannelCount,
   CFG_ScanClockSource,                /* Reserved for later using */
   CFG_ScanClockRate,                  /* Reserved for later using */
   CFG_ScanCount,                      /* Reserved for later using */
   CFG_TriggerSource,
   CFG_TriggerSourceEdge,
   CFG_TriggerSourceLevel,
   CFG_TriggerDelayCount,
   CFG_TriggerAction,
   CFG_Trigger1Source,                 /* Reserved for later using */
   CFG_Trigger1SourceEdge,             /* Reserved for later using */
   CFG_Trigger1SourceLevel,            /* Reserved for later using */
   CFG_Trigger1DelayCount,             /* Reserved for later using */
   CFG_Trigger1Action,                 /* Reserved for later using */
   CFG_ParentSignalConnectionChannel,
   CFG_ParentCjcConnectionChannel,
   CFG_ParentControlPort,

   /*-----------------------------------------------------------------
   * component specified Property IDs -- DIO
   *-----------------------------------------------------------------*/
   CFG_FeaturePortsCount,
   CFG_FeaturePortsType,
   CFG_FeatureNoiseFilterOfChannels,
   CFG_FeatureNoiseFilterBlockTimeRange,     /* Reserved for later using */
   CFG_FeatureDiintTriggerEdges,
   CFG_FeatureDiintOfChannels,
   CFG_FeatureDiintGateOfChannels,
   CFG_FeatureDiCosintOfChannels,
   CFG_FeatureDiPmintOfChannels,
   CFG_FeatureSnapEventSources,
   CFG_FeatureDiSnapEventSources = CFG_FeatureSnapEventSources, /*For compatible*/
   CFG_FeatureDoFreezeSignalSources,            /* Reserved for later using */
   CFG_FeatureDoReflectWdtFeedIntervalRange,    /* Reserved for later using */

   CFG_FeatureDiPortScanMethod,                 /* Reserved for later using */
   CFG_FeatureDiConvertClockSources,            /* Reserved for later using */
   CFG_FeatureDiConvertClockRateRange,          /* Reserved for later using */
   CFG_FeatureDiScanClockSources,
   CFG_FeatureDiScanClockRateRange,             /* Reserved for later using */
   CFG_FeatureDiScanCountMax,
   CFG_FeatureDiTriggersCount,
   CFG_FeatureDiTriggerSources,
   CFG_FeatureDiTriggerActions,
   CFG_FeatureDiTriggerDelayCountRange,
   CFG_FeatureDiTrigger1Sources,
   CFG_FeatureDiTrigger1Actions,
   CFG_FeatureDiTrigger1DelayCountRange,

   CFG_FeatureDoPortScanMethod,                 /* Reserved for later using */
   CFG_FeatureDoConvertClockSources,            /* Reserved for later using */
   CFG_FeatureDoConvertClockRateRange,          /* Reserved for later using */
   CFG_FeatureDoScanClockSources,
   CFG_FeatureDoScanClockRateRange,             /* Reserved for later using */
   CFG_FeatureDoScanCountMax,
   CFG_FeatureDoTriggersCount,
   CFG_FeatureDoTriggerSources,
   CFG_FeatureDoTriggerActions,
   CFG_FeatureDoTriggerDelayCountRange,
   CFG_FeatureDoTrigger1Sources,
   CFG_FeatureDoTrigger1Actions,
   CFG_FeatureDoTrigger1DelayCountRange,

   CFG_DirectionOfPorts,
   CFG_DiDataMaskOfPorts,
   CFG_DoDataMaskOfPorts,

   CFG_NoiseFilterOverallBlockTime,              /* Reserved for later using */
   CFG_NoiseFilterEnabledChannels,
   CFG_DiintTriggerEdgeOfChannels,
   CFG_DiintGateEnabledChannels,
   CFG_DiCosintEnabledChannels,
   CFG_DiPmintEnabledChannels,
   CFG_DiPmintValueOfPorts,
   CFG_DoInitialStateOfPorts,                   /* Reserved for later using */
   CFG_DoFreezeEnabled,                         /* Reserved for later using */
   CFG_DoFreezeSignalState,                     /* Reserved for later using */
   CFG_DoReflectWdtFeedInterval,                /* Reserved for later using */
   CFG_DoReflectWdtLockValue,                   /* Reserved for later using */
   CFG_DiSectionDataCount,
   CFG_DiConvertClockSource,
   CFG_DiConvertClockRatePerPort,
   CFG_DiScanPortStart,
   CFG_DiScanPortCount,
   CFG_DiScanClockSource,
   CFG_DiScanClockRate,
   CFG_DiScanCount,
   CFG_DiTriggerAction,
   CFG_DiTriggerSource,
   CFG_DiTriggerSourceEdge,
   CFG_DiTriggerSourceLevel,                    /* Reserved for later using */
   CFG_DiTriggerDelayCount,
   CFG_DiTrigger1Action,
   CFG_DiTrigger1Source,
   CFG_DiTrigger1SourceEdge,
   CFG_DiTrigger1SourceLevel,                   /* Reserved for later using */
   CFG_DiTrigger1DelayCount,

   CFG_DoSectionDataCount,
   CFG_DoConvertClockSource,
   CFG_DoConvertClockRatePerPort,
   CFG_DoScanPortStart,
   CFG_DoScanPortCount,
   CFG_DoScanClockSource,
   CFG_DoScanClockRate,
   CFG_DoScanCount,
   CFG_DoTriggerAction,
   CFG_DoTriggerSource,
   CFG_DoTriggerSourceEdge,
   CFG_DoTriggerSourceLevel,                    /* Reserved for later using */
   CFG_DoTriggerDelayCount,
   CFG_DoTrigger1Action,
   CFG_DoTrigger1Source,
   CFG_DoTrigger1SourceEdge,
   CFG_DoTrigger1SourceLevel,                   /* Reserved for later using */
   CFG_DoTrigger1DelayCount,

   /*-----------------------------------------------------------------
   * component specified Property IDs -- Counter/Timer
   *-----------------------------------------------------------------*/
   /*common feature*/
   CFG_FeatureCapabilitiesOfCounter0 = 174,
   CFG_FeatureCapabilitiesOfCounter1,
   CFG_FeatureCapabilitiesOfCounter2,
   CFG_FeatureCapabilitiesOfCounter3,
   CFG_FeatureCapabilitiesOfCounter4,
   CFG_FeatureCapabilitiesOfCounter5,
   CFG_FeatureCapabilitiesOfCounter6,
   CFG_FeatureCapabilitiesOfCounter7,

   /*primal counter features*/
   CFG_FeatureChipOperationModes = 206,
   CFG_FeatureChipSignalCountingTypes,

   /*timer/pulse features*/
   CFG_FeatureTmrCascadeGroups = 211,

   /*frequency measurement features*/
   CFG_FeatureFmMethods = 213,

   /*Primal counter properties */
   CFG_ChipOperationModeOfCounters = 220,
   CFG_ChipSignalCountingTypeOfCounters,
   CFG_ChipLoadValueOfCounters,
   CFG_ChipHoldValueOfCounters,
   CFG_ChipOverCompareValueOfCounters,
   CFG_ChipUnderCompareValueOfCounters,
   CFG_ChipOverCompareEnabledCounters,
   CFG_ChipUnderCompareEnabledCounters,

   /*frequency measurement properties*/
   CFG_FmMethodOfCounters = 231,
   CFG_FmCollectionPeriodOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.1
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_DevicePrivateRegionLength,
   CFG_SaiAutoConvertClockRate,
   CFG_SaiAutoConvertChannelStart,
   CFG_SaiAutoConvertChannelCount,
   CFG_ExtPauseSignalEnabled,
   CFG_ExtPauseSignalPolarity,
   CFG_OrderOfChannels,
   CFG_InitialStateOfChannels,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.2: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   /*primal counter features*/
   CFG_FeatureChipClkSourceOfCounter0 = 242,
   CFG_FeatureChipClkSourceOfCounter1,
   CFG_FeatureChipClkSourceOfCounter2,
   CFG_FeatureChipClkSourceOfCounter3,
   CFG_FeatureChipClkSourceOfCounter4,
   CFG_FeatureChipClkSourceOfCounter5,
   CFG_FeatureChipClkSourceOfCounter6,
   CFG_FeatureChipClkSourceOfCounter7,

   CFG_FeatureChipGateSourceOfCounter0,
   CFG_FeatureChipGateSourceOfCounter1,
   CFG_FeatureChipGateSourceOfCounter2,
   CFG_FeatureChipGateSourceOfCounter3,
   CFG_FeatureChipGateSourceOfCounter4,
   CFG_FeatureChipGateSourceOfCounter5,
   CFG_FeatureChipGateSourceOfCounter6,
   CFG_FeatureChipGateSourceOfCounter7,

   CFG_FeatureChipValueRegisters,

   /*one-shot features*/
   CFG_FeatureOsClkSourceOfCounter0,
   CFG_FeatureOsClkSourceOfCounter1,
   CFG_FeatureOsClkSourceOfCounter2,
   CFG_FeatureOsClkSourceOfCounter3,
   CFG_FeatureOsClkSourceOfCounter4,
   CFG_FeatureOsClkSourceOfCounter5,
   CFG_FeatureOsClkSourceOfCounter6,
   CFG_FeatureOsClkSourceOfCounter7,

   CFG_FeatureOsGateSourceOfCounter0,
   CFG_FeatureOsGateSourceOfCounter1,
   CFG_FeatureOsGateSourceOfCounter2,
   CFG_FeatureOsGateSourceOfCounter3,
   CFG_FeatureOsGateSourceOfCounter4,
   CFG_FeatureOsGateSourceOfCounter5,
   CFG_FeatureOsGateSourceOfCounter6,
   CFG_FeatureOsGateSourceOfCounter7,

   /*Pulse width measurement features*/
   CFG_FeaturePiCascadeGroups,

   /*Primal counter properties */
   CFG_ChipClkSourceOfCounters = 279, 
   CFG_ChipGateSourceOfCounters,

   /*one-shot properties*/
   CFG_OsClkSourceOfCounters, 
   CFG_OsGateSourceOfCounters,
   CFG_OsDelayCountOfCounters,

   /*Timer pulse properties*/
   CFG_TmrFrequencyOfCounters,

   /*Pulse width modulation properties*/
   CFG_PoHiPeriodOfCounters,
   CFG_PoLoPeriodOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.3: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   /*Event counting features & properties*/
   CFG_FeatureEcClkPolarities,
   CFG_FeatureEcGatePolarities,
   CFG_FeatureEcGateControlOfCounters,

   CFG_EcClkPolarityOfCounters,
   CFG_EcGatePolarityOfCounters,
   CFG_EcGateEnabledOfCounters,

   /*one-shot features & properties*/
   CFG_FeatureOsClkPolarities,
   CFG_FeatureOsGatePolarities,
   CFG_FeatureOsOutSignals,

   CFG_OsClkPolarityOfCounters,
   CFG_OsGatePolarityOfCounters,
   CFG_OsOutSignalOfCounters,

   /*timer/pulse features & properties*/
   CFG_FeatureTmrGateControlOfCounters,
   CFG_FeatureTmrGatePolarities,
   CFG_FeatureTmrOutSignals,
   CFG_FeatureTmrFrequencyRange,

   CFG_TmrGateEnabledOfCounters,
   CFG_TmrGatePolarityOfCounters,
   CFG_TmrOutSignalOfCounters,

   /*Pulse width modulation features & properties*/
   CFG_FeaturePoGateControlOfCounters,
   CFG_FeaturePoGatePolarities,
   CFG_FeaturePoHiPeriodRange,
   CFG_FeaturePoLoPeriodRange,
   CFG_FeaturePoOutCountRange,

   CFG_PoGateEnabledOfCounters,
   CFG_PoGatePolarityOfCounters,
   CFG_PoOutCountOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.4: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureChipClkPolarities,
   CFG_FeatureChipGatePolarities,
   CFG_FeatureChipOutSignals,

   CFG_ChipClkPolarityOfCounters,
   CFG_ChipGatePolarityOfCounters,
   CFG_ChipOutSignalOfCounters,
   
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.5: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureOsDelayCountRange,
   
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.6: new features & properties of counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureUdCountingTypes,
   CFG_FeatureUdInitialValues,
   CFG_UdCountingTypeOfCounters,
   CFG_UdInitialValueOfCounters,
   CFG_UdCountValueResetTimesByIndexs,
   
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.7: new features & properties of AI
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureFilterTypes,
   CFG_FeatureFilterCutoffFreqRange,
   CFG_FeatureFilterCutoffFreq1Range,
   CFG_FilterTypeOfChannels,
   CFG_FilterCutoffFreqOfChannels,
   CFG_FilterCutoffFreq1OfChannels,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.8: new features & properties of DIO
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureDiOpenStatePorts,
   CFG_FeatureDiOpenStates,
   CFG_DiOpenStatesOfPorts,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v1.9: new features & properties of PWM counter
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeaturePoOutSignals,
   CFG_PoOutSignalOfCounters,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.0: new features & properties of AO/AI Trigger 
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureTriggerSourceVRG,
   CFG_FeatureTriggerHysteresisIndexMax,
   CFG_FeatureTriggerHysteresisIndexStep,
   CFG_TriggerHysteresisIndex,
   CFG_FeatureTrigger1SourceVRG,
   CFG_FeatureTrigger1HysteresisIndexMax,
   CFG_FeatureTrigger1HysteresisIndexStep,
   CFG_Trigger1HysteresisIndex,
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.1: new features & properties of AI
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureCouplingTypes,
   CFG_CouplingTypeOfChannels,
   CFG_FeatureImpedanceTypes,
   CFG_ImpedanceTypeOfChannels,
   CFG_FaiRecordCount,
   
   CFG_FeatureTriggerFilterTypes,
   CFG_FeatureTriggerFilterCutoffFreqRange,
   CFG_TriggerFilterType,
   CFG_Trigger1FilterType,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.2: new features & properties of AI
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_DiInversePorts,
   CFG_FeatureRetriggerable,
   CFG_ScanEnabledChannels,
   CFG_FeatureIepeTypes,
   CFG_IepeTypeOfChannels,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.3: new features & properties of AI
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_TriggerFilterCutoffFreq,
   CFG_Trigger1FilterCutoffFreq,
   CFG_FeatureTrigger2Sources,            /* Reserved for later using */
   CFG_FeatureTrigger2Actions,            /* Reserved for later using */
   CFG_FeatureTrigger2DelayCountRange,    /* Reserved for later using */
   CFG_FeatureTrigger2SourceVRG,
   CFG_FeatureTrigger2HysteresisIndexMax,
   CFG_FeatureTrigger2HysteresisIndexStep,

   CFG_Trigger2Source,                    /* Reserved for later using */
   CFG_Trigger2SourceEdge,                /* Reserved for later using */
   CFG_Trigger2SourceLevel,               /* Reserved for later using */
   CFG_Trigger2DelayCount,                /* Reserved for later using */
   CFG_Trigger2Action,                    /* Reserved for later using */
   CFG_Trigger2HysteresisIndex,
   CFG_Trigger2FilterType,
   CFG_Trigger2FilterCutoffFreq,
   
   CFG_FeatureTrigger3Sources,            /* Reserved for later using */
   CFG_FeatureTrigger3Actions,            /* Reserved for later using */
   CFG_FeatureTrigger3DelayCountRange,    /* Reserved for later using */
   CFG_FeatureTrigger3SourceVRG,
   CFG_FeatureTrigger3HysteresisIndexMax,
   CFG_FeatureTrigger3HysteresisIndexStep,

   CFG_Trigger3Source,                    /* Reserved for later using */
   CFG_Trigger3SourceEdge,                /* Reserved for later using */
   CFG_Trigger3SourceLevel,               /* Reserved for later using */
   CFG_Trigger3DelayCount,                /* Reserved for later using */
   CFG_Trigger3Action,                    /* Reserved for later using */
   CFG_Trigger3HysteresisIndex,
   CFG_Trigger3FilterType,
   CFG_Trigger3FilterCutoffFreq,
   
   CFG_FeatureTimeStampRes,
   CFG_RecordSectionLength,
   CFG_RecordSectionCount,
   CFG_FeatureConnectionTypes,
   CFG_FeatureOverallConnection, 

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.4: new features & properties
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureMeasurementTimeoutRange, 
   CFG_MeasurementTimeout,

   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   // v2.5: new features & properties of DIO
   //##xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   CFG_FeatureDoInitialStateDepository,
   CFG_DeviceLocateEnabled,


   // <<<---- end of public property ID <<<---- 

   //////////////////////////////////////////////////////////////////////////
   //                                                                      //
   // INTERNAL USED ONLY property ID starts from here.                     //
   //                                                                      //
   // CAUTION: public property must be inserted before this line.          //
   //                                                                      //
   //////////////////////////////////////////////////////////////////////////
   CFG_FeatureInternalClockSourceOfCounters  = 0x60000000 ,
   CFG_InternalClockSourceOfCounters,
   CFG_FeaturePiClkSourceOfCounters,
   CFG_PiClkSourceOfCounters,
   CFG_DoConfig,
   CFG_TimeBase,
   CFG_EnableFifo,
   CFG_XferMode,
   CFG_AIRangeJumper,
   CFG_Jumper5L,
   CFG_Jumper8,
   CFG_InternalGateSourceOfCounters
} PropertyId;

#define BioFailed(c)  ((unsigned)(c) >= (unsigned)0xE0000000)   

typedef enum tagErrorCode {
   /// <summary>
   /// The operation is completed successfully. 
   /// </summary>
   Success = 0, 

   ///************************************************************************
   /// warning                                                              
   ///************************************************************************
   /// <summary>
   /// The interrupt resource is not available. 
   /// </summary>
   WarningIntrNotAvailable = 0xA0000000,

   /// <summary>
   /// The parameter is out of the range. 
   /// </summary>
   WarningParamOutOfRange = 0xA0000001,

   /// <summary>
   /// The property value is out of range. 
   /// </summary>
   WarningPropValueOutOfRange = 0xA0000002,

   /// <summary>
   /// The property value is not supported. 
   /// </summary>
   WarningPropValueNotSpted = 0xA0000003,

   /// <summary>
   /// The property value conflicts with the current state.
   /// </summary>
   WarningPropValueConflict = 0xA0000004,

   /// <summary>
   /// The value range of all channels in a group should be same, 
   /// such as 4~20mA of PCI-1724.
   /// </summary>
   WarningVrgOfGroupNotSame = 0xA0000005,

   ///***********************************************************************
   /// error                                                                
   ///***********************************************************************
   /// <summary>
   /// The handle is NULL or its type doesn't match the required operation. 
   /// </summary>
   ErrorHandleNotValid = 0xE0000000,

   /// <summary>
   /// The parameter value is out of range.
   /// </summary>
   ErrorParamOutOfRange = 0xE0000001,

   /// <summary>
   /// The parameter value is not supported.
   /// </summary>
   ErrorParamNotSpted = 0xE0000002,

   /// <summary>
   /// The parameter value format is not the expected. 
   /// </summary>
   ErrorParamFmtUnexpted = 0xE0000003,

   /// <summary>
   /// Not enough memory is available to complete the operation. 
   /// </summary>
   ErrorMemoryNotEnough = 0xE0000004,

   /// <summary>
   /// The data buffer is null. 
   /// </summary>
   ErrorBufferIsNull = 0xE0000005,

   /// <summary>
   /// The data buffer is too small for the operation. 
   /// </summary>
   ErrorBufferTooSmall = 0xE0000006,

   /// <summary>
   /// The data length exceeded the limitation. 
   /// </summary>
   ErrorDataLenExceedLimit = 0xE0000007,

   /// <summary>
   /// The required function is not supported. 
   /// </summary>
   ErrorFuncNotSpted = 0xE0000008,

   /// <summary>
   /// The required event is not supported. 
   /// </summary>
   ErrorEventNotSpted = 0xE0000009,

   /// <summary>
   /// The required property is not supported. 
   /// </summary>
   ErrorPropNotSpted = 0xE000000A, 

   /// <summary>
   /// The required property is read-only. 
   /// </summary>
   ErrorPropReadOnly = 0xE000000B,

   /// <summary>
   /// The specified property value conflicts with the current state.
   /// </summary>
   ErrorPropValueConflict = 0xE000000C,

   /// <summary>
   /// The specified property value is out of range.
   /// </summary>
   ErrorPropValueOutOfRange = 0xE000000D,

   /// <summary>
   /// The specified property value is not supported. 
   /// </summary>
   ErrorPropValueNotSpted = 0xE000000E,

   /// <summary>
   /// The handle hasn't own the privilege of the operation the user wanted. 
   /// </summary>
   ErrorPrivilegeNotHeld = 0xE000000F,

   /// <summary>
   /// The required privilege is not available because someone else had own it. 
   /// </summary>
   ErrorPrivilegeNotAvailable = 0xE0000010,

   /// <summary>
   /// The driver of specified device was not found. 
   /// </summary>
   ErrorDriverNotFound = 0xE0000011,

   /// <summary>
   /// The driver version of the specified device mismatched. 
   /// </summary>
   ErrorDriverVerMismatch = 0xE0000012,

   /// <summary>
   /// The loaded driver count exceeded the limitation. 
   /// </summary>
   ErrorDriverCountExceedLimit = 0xE0000013,

   /// <summary>
   /// The device is not opened. 
   /// </summary>
   ErrorDeviceNotOpened = 0xE0000014,      

   /// <summary>
   /// The required device does not exist. 
   /// </summary>
   ErrorDeviceNotExist = 0xE0000015,

   /// <summary>
   /// The required device is unrecognized by driver. 
   /// </summary>
   ErrorDeviceUnrecognized = 0xE0000016,

   /// <summary>
   /// The configuration data of the specified device is lost or unavailable. 
   /// </summary>
   ErrorConfigDataLost = 0xE0000017,

   /// <summary>
   /// The function is not initialized and can't be started. 
   /// </summary>
   ErrorFuncNotInited = 0xE0000018,

   /// <summary>
   /// The function is busy. 
   /// </summary>
   ErrorFuncBusy = 0xE0000019,

   /// <summary>
   /// The interrupt resource is not available. 
   /// </summary>
   ErrorIntrNotAvailable = 0xE000001A,

   /// <summary>
   /// The DMA channel is not available. 
   /// </summary>
   ErrorDmaNotAvailable = 0xE000001B,

   /// <summary>
   /// Time out when reading/writing the device. 
   /// </summary>
   ErrorDeviceIoTimeOut = 0xE000001C,

   /// <summary>
   /// The given signature does not match with the device current one.
   /// </summary>
   ErrorSignatureNotMatch = 0xE000001D,

   /// <summary>
   /// The function cannot be executed while the buffered AI is running.
   /// </summary>
   ErrorFuncConflictWithBfdAi = 0xE000001E,

   /// <summary>
   /// The value range is not available in single-ended mode.
   /// </summary>
   ErrorVrgNotAvailableInSeMode = 0xE000001F,

   /// <summary>
   /// The value range is not available in 50omh input impedance mode.
   /// </summary>
   ErrorVrgNotAvailableIn50ohmMode  = 0xE0000020,

   /// <summary>
   /// The coupling type is not available in 50omh input impedance mode.
   /// </summary>
   ErrorCouplingNotAvailableIn50ohmMode  = 0xE0000021,

   /// <summary>
   /// The coupling type is not available in IEPE mode.
   /// </summary>
   ErrorCouplingNotAvailableInIEPEMode  = 0xE0000022,

   /// <summary>
   /// Communication is failed when reading/writing the device.
   /// </summary>
   ErrorDeviceCommunicationFailed  = 0xE0000023,

   /// <summary>
   /// Undefined error 
   /// </summary>
   ErrorUndefined = 0xE000FFFF,
} ErrorCode;

// Advantech CardType ID 
typedef enum tagProductId {
   BD_DEMO   = 0x00,      // demo board
   BD_PCL818 = 0x05,      // PCL-818 board
   BD_PCL818H = 0x11,   // PCL-818H
   BD_PCL818L = 0x21,   // PCL-818L
   BD_PCL818HG = 0x22,   // PCL-818HG
   BD_PCL818HD = 0x2b,   // PCL-818HD
   BD_PCM3718 = 0x37,   // PCM-3718
   BD_PCM3724 = 0x38,   // PCM-3724
   BD_PCM3730 = 0x5a,   // PCM-3730
   BD_PCI1750 = 0x5e,   // PCI-1750
   BD_PCI1751 = 0x5f,   // PCI-1751
   BD_PCI1710 = 0x60,   // PCI-1710
   BD_PCI1712 = 0x61,   // PCI-1712
   BD_PCI1710HG = 0x67,   // PCI-1710HG
   BD_PCI1711 = 0x73,   // PCI-1711
   BD_PCI1711L = 0x75,   // PCI-1711L 
   BD_PCI1713 = 0x68,   // PCI-1713
   BD_PCI1753 = 0x69,   // PCI-1753
   BD_PCI1760 = 0x6a,   // PCI-1760
   BD_PCI1720 = 0x6b,   // PCI-1720
   BD_PCM3718H = 0x6d,   // PCM-3718H
   BD_PCM3718HG = 0x6e,   // PCM-3718HG
   BD_PCI1716 = 0x74,   // PCI-1716
   BD_PCI1731 = 0x75,   // PCI-1731
   BD_PCI1754 = 0x7b,   // PCI-1754
   BD_PCI1752 = 0x7c,   // PCI-1752
   BD_PCI1756 = 0x7d,   // PCI-1756
   BD_PCM3725 = 0x7f,   // PCM-3725
   BD_PCI1762 = 0x80,   // PCI-1762
   BD_PCI1721 = 0x81,   // PCI-1721
   BD_PCI1761 = 0x82,   // PCI-1761
   BD_PCI1723 = 0x83,   // PCI-1723
   BD_PCI1730 = 0x87,   // PCI-1730
   BD_PCI1733 = 0x88,   // PCI-1733
   BD_PCI1734 = 0x89,   // PCI-1734
   BD_PCI1710L = 0x90,   // PCI-1710L
   BD_PCI1710HGL = 0x91,// PCI-1710HGL
   BD_PCM3712 = 0x93,   // PCM-3712
   BD_PCM3723 = 0x94,   // PCM-3723
   BD_PCI1780 = 0x95,   // PCI-1780
   BD_MIC3756 = 0x96,   // MIC-3756
   BD_PCI1755 = 0x97,   // PCI-1755
   BD_PCI1714 = 0x98,   // PCI-1714
   BD_PCI1757 = 0x99,   // PCI-1757
   BD_MIC3716 = 0x9A,   // MIC-3716
   BD_MIC3761 = 0x9B,   // MIC-3761
   BD_MIC3753 = 0x9C,      // MIC-3753
   BD_MIC3780 = 0x9D,      // MIC-3780
   BD_PCI1724 = 0x9E,      // PCI-1724
   BD_PCI1758UDI = 0xA3,   // PCI-1758UDI
   BD_PCI1758UDO = 0xA4,   // PCI-1758UDO
   BD_PCI1747 = 0xA5,      // PCI-1747
   BD_PCM3780 = 0xA6,      // PCM-3780 
   BD_MIC3747 = 0xA7,      // MIC-3747
   BD_PCI1758UDIO = 0xA8,   // PCI-1758UDIO
   BD_PCI1712L = 0xA9,      // PCI-1712L
   BD_PCI1763UP = 0xAC,      // PCI-1763UP
   BD_PCI1736UP = 0xAD,      // PCI-1736UP
   BD_PCI1714UL = 0xAE,      // PCI-1714UL
   BD_MIC3714 = 0xAF,      // MIC-3714
   BD_PCM3718HO = 0xB1,      // PCM-3718HO
   BD_PCI1741U = 0xB3,      // PCI-1741U
   BD_MIC3723 = 0xB4,      // MIC-3723 
   BD_PCI1718HDU = 0xB5,   // PCI-1718HDU
   BD_MIC3758DIO = 0xB6,   // MIC-3758DIO
   BD_PCI1727U = 0xB7,      // PCI-1727U
   BD_PCI1718HGU = 0xB8,   // PCI-1718HGU
   BD_PCI1715U = 0xB9,      // PCI-1715U
   BD_PCI1716L = 0xBA,      // PCI-1716L
   BD_PCI1735U = 0xBB,      // PCI-1735U
   BD_USB4711 = 0xBC,      // USB4711
   BD_PCI1737U = 0xBD,      // PCI-1737U
   BD_PCI1739U = 0xBE,      // PCI-1739U
   BD_PCI1742U = 0xC0,      // PCI-1742U
   BD_USB4718 = 0xC6,      // USB-4718
   BD_MIC3755 = 0xC7,      // MIC3755
   BD_USB4761 = 0xC8,      // USB4761
   BD_PCI1784 = 0XCC,      // PCI-1784
   BD_USB4716 = 0xCD,      // USB4716
   BD_PCI1752U = 0xCE,      // PCI-1752U
   BD_PCI1752USO = 0xCF,   // PCI-1752USO
   BD_USB4751 = 0xD0,      // USB4751
   BD_USB4751L = 0xD1,      // USB4751L
   BD_USB4750 = 0xD2,      // USB4750
   BD_MIC3713 = 0xD3,      // MIC-3713
   BD_USB4711A = 0xD8,      // USB4711A
   BD_PCM3753P = 0xD9,      // PCM3753P
   BD_PCM3784  = 0xDA,      // PCM3784
   BD_PCM3761I = 0xDB,     // PCM-3761I
   BD_MIC3751  = 0xDC,     // MIC-3751
   BD_PCM3730I = 0xDD,     // PCM-3730I
   BD_PCM3813I = 0xE0,     // PCM-3813I
   BD_PCIE1744   = 0xE1,     //PCIE-1744
   BD_PCI1730U   = 0xE2,       // PCI-1730U
   BD_PCI1760U   = 0xE3,      //PCI-1760U
   BD_MIC3720   = 0xE4,      //MIC-3720
   BD_PCM3810I = 0xE9,     // PCM-3810I
   BD_USB4702  = 0xEA,     // USB4702
   BD_USB4704  = 0xEB,     // USB4704
   BD_PCM3810I_HG = 0xEC,  // PCM-3810I_HG
   BD_PCI1713U = 0xED,      // PCI-1713U 

   // !!!BioDAQ only Product ID starts from here!!!
   BD_PCI1706U   = 0x800,
   BD_PCI1706MSU = 0x801,
   BD_PCI1706UL  = 0x802,
   BD_PCIE1752   = 0x803,
   BD_PCIE1754   = 0x804,
   BD_PCIE1756   = 0x805,
   BD_MIC1911    = 0x806,
   BD_MIC3750    = 0x807,
   BD_MIC3711    = 0x808,
   BD_PCIE1730   = 0x809,
   BD_PCI1710_ECU = 0x80A,
   BD_PCI1720_ECU = 0x80B,
   BD_PCIE1760   = 0x80C,
   BD_PCIE1751   = 0x80D,
   BD_ECUP1706   = 0x80E,
   BD_PCIE1753   = 0x80F,
   BD_PCIE1810   = 0x810,
   BD_ECUP1702L  = 0x811,
   BD_PCIE1816   = 0x812,
   BD_PCM27D24DI = 0x813,
   BD_PCIE1816H  = 0x814,
   BD_PCIE1840   = 0x815,
   BD_PCL725     = 0x816,
   BD_PCI176E    = 0x817,
   BD_PCIE1802   = 0x818,
   BD_AIISE730   = 0x819,
   BD_PCIE1812   = 0x81A,
   BD_MIC1810    = 0x81B,
   BD_PCIE1802L  = 0x81C,
   BD_PCIE1813   = 0x81D,
   BD_PCIE1840L  = 0x81E,
   BD_PCIE1730H  = 0x81F,
   BD_PCIE1756H  = 0x820,
   BD_PCIERXM01  = 0x821,          // PCIe-RXM01
   BD_MIC1816    = 0x822,
   BD_USB5830    = 0x823,
   BD_USB5850    = 0x824,
   BD_USB5860    = 0x825,
   BD_VPX1172    = 0x826,
   BD_USB5855    = 0x827,
   BD_USB5856    = 0x828,
   BD_USB5862    = 0x829,
   BD_PCIE1840T  = 0x82A,
   BD_AudioCard  = 0x82B,
   BD_AIIS1750   = 0x82C,
   BD_PCIE1840HL = 0x82D,
   BD_PCIE1765   = 0x82E,
   BD_PCIE1761H  = 0x82F,
   BD_PCIE1762H  = 0x830,
   
} ProductId;

END_NAMEAPCE_AUTOMATION_BDAQ

#endif // _BDAQ_TYPES_DEFINED

// **********************************************************
// Bionic DAQ COM style class library
// **********************************************************
#if !defined(_BDAQ_TYPES_ONLY) && !defined(_BDAQ_COM_STYLE_CLASS_LIB)
#define _BDAQ_COM_STYLE_CLASS_LIB

#  include <stdlib.h>
#  if defined(_WIN32) || defined(WIN32)
#     include <Windows.h>
#  endif

BEGIN_NAMEAPCE_AUTOMATION_BDAQ

// **********************************************************
// types definition
// **********************************************************
typedef struct tagDeviceInformation{
   int32      DeviceNumber;
   AccessMode DeviceMode;
   int32      ModuleIndex;
   wchar_t    Description[MAX_DEVICE_DESC_LEN]; 

#if defined(__cplusplus) && !defined(_BDAQ_C_INTERFACE)
   explicit tagDeviceInformation(int32 deviceNumber = -1, AccessMode mode = ModeWriteWithReset, int32 moduleIndex = 0)
   {
      Init(deviceNumber, NULL, mode, moduleIndex);
   }
   explicit tagDeviceInformation(wchar_t const *deviceDesc, AccessMode mode = ModeWriteWithReset, int32 moduleIndex = 0)
   {
      Init(-1, deviceDesc, mode, moduleIndex);
   }
   void Init(int32 deviceNumber, wchar_t const *deviceDesc, AccessMode mode, int32 moduleIndex)
   {
      DeviceNumber = deviceNumber;
      DeviceMode   = mode;
      ModuleIndex  = moduleIndex;
      if (deviceDesc == NULL) Description[0] = L'\0';
      else {
         for (int i = 0; i < (MAX_DEVICE_DESC_LEN - 1) && (Description[i] = *deviceDesc++);  ++i){}
         Description[MAX_DEVICE_DESC_LEN - 1] = L'\0';
      }
   }
#endif
} DeviceInformation;

typedef struct tagDeviceTreeNode{
   int32      DeviceNumber;
   int32      ModulesIndex[8];
   wchar_t    Description[MAX_DEVICE_DESC_LEN];
}DeviceTreeNode;

typedef struct tagDeviceEventArgs {
   // ^_^
   // at present nothing is needed to be passed to user
   // it is just a place-holder for later extension.
   int32 dummy[1];
}DeviceEventArgs; 

typedef struct tagBfdAiEventArgs {
   int32 Offset; // offset of the new data
   int32 Count;  // amount of the new data
}BfdAiEventArgs;

typedef struct tagBfdAoEventArgs {
   int32 Offset; // offset of blank area
   int32 Count;  // amount of blank area
}BfdAoEventArgs;

typedef struct tagBfdDiEventArgs {
   int32 Offset; // offset of the new data
   int32 Count;  // amount of the new data
}BfdDiEventArgs;

typedef struct tagBfdDoEventArgs {
   int32 Offset; // offset of blank area
   int32 Count;  // amount of blank area
}BfdDoEventArgs;

typedef struct tagDiSnapEventArgs{
   int32 SrcNum;
   int32 Length;
   uint8 PortData[MAX_DIO_PORT_COUNT];
}DiSnapEventArgs;

typedef struct tagCntrEventArgs{
   int32 Channel;
}CntrEventArgs;

typedef struct tagUdCntrEventArgs{
   int32 SrcId;
   int32 Length;
   int32 Data[MAX_CNTR_CH_COUNT];
}UdCntrEventArgs;

typedef struct tagPulseWidth{
   double HiPeriod;
   double LoPeriod;
}PulseWidth;

typedef enum tagControlState
{
   Idle = 0,
   Ready,
   Running,
   Stopped
} ControlState;

// **********************************************************
// classes definition
// **********************************************************
#if defined(__cplusplus) && !defined(_BDAQ_C_INTERFACE)

// ----------------------------------------------------------
// common classes
// ----------------------------------------------------------
/* Interface ICollection */
   template<class T>
   class ICollection
   {
   public:
      virtual void  BDAQCALL Dispose() = 0;   // destroy the instance
      virtual int32 BDAQCALL getCount() = 0;
      virtual T &   BDAQCALL getItem(int32 index) = 0;
   };

/* Interface AnalogChannel */
   class AnalogChannel
   {
   public:
      virtual int32      BDAQCALL getChannel() = 0;
      virtual ValueRange BDAQCALL getValueRange() = 0;
      virtual ErrorCode  BDAQCALL setValueRange(ValueRange value) = 0;
   };

/* Interface AnalogInputChannel */
   class AnalogInputChannel : public AnalogChannel
   {
   public:
      virtual AiSignalType   BDAQCALL getSignalType() = 0;
      virtual ErrorCode      BDAQCALL setSignalType(AiSignalType value) = 0;
      virtual BurnoutRetType BDAQCALL getBurnoutRetType() = 0;
      virtual ErrorCode      BDAQCALL setBurnoutRetType(BurnoutRetType value) = 0;
      virtual double         BDAQCALL getBurnoutRetValue() = 0;
      virtual ErrorCode      BDAQCALL setBurnoutRetValue(double value) = 0;

      //new : Coupling & IEPE
      virtual CouplingType   BDAQCALL getCouplingType() = 0;
      virtual ErrorCode      BDAQCALL setCouplingType(CouplingType value) = 0;
      virtual IepeType       BDAQCALL getIepeType() = 0;
      virtual ErrorCode      BDAQCALL setIepeType(IepeType value) = 0;
   };

/* Interface CjcSetting */
   class CjcSetting
   {
   public:
      virtual int32     BDAQCALL getChannel() = 0;
      virtual ErrorCode BDAQCALL setChannel(int32 ch) = 0;
      virtual double    BDAQCALL getValue() = 0;
      virtual ErrorCode BDAQCALL setValue(double value) = 0;
   };

/* Interface ScanChannel */
   class ScanChannel
   {
   public:
      virtual int32     BDAQCALL getChannelStart() = 0;
      virtual ErrorCode BDAQCALL setChannelStart(int32 value) = 0;
      virtual int32     BDAQCALL getChannelCount() = 0;
      virtual ErrorCode BDAQCALL setChannelCount(int32 value) = 0;
      virtual int32     BDAQCALL getSamples() = 0;
      virtual ErrorCode BDAQCALL setSamples(int32 value) = 0;
      virtual int32     BDAQCALL getIntervalCount() = 0;
      virtual ErrorCode BDAQCALL setIntervalCount(int32 value) = 0;
   };

/* Interface ConvertClock */
   class ConvertClock
   {
   public:
      virtual SignalDrop BDAQCALL getSource() = 0;
      virtual ErrorCode  BDAQCALL setSource(SignalDrop value) = 0;
      virtual double     BDAQCALL getRate() = 0;
      virtual ErrorCode  BDAQCALL setRate(double value) = 0;
   };

/* Interface ScanClock */
   class ScanClock
   {
   public:
      virtual SignalDrop BDAQCALL getSource() = 0;
      virtual ErrorCode  BDAQCALL setSource(SignalDrop value) = 0;
      virtual double     BDAQCALL getRate() = 0;
      virtual ErrorCode  BDAQCALL setRate(double value) = 0;
      virtual int32      BDAQCALL getScanCount() = 0;
      virtual ErrorCode  BDAQCALL setScanCount(int32 value) = 0;
   };

/* Interface Trigger */
   class Trigger
   {
   public:
      virtual SignalDrop    BDAQCALL getSource() = 0;
      virtual ErrorCode     BDAQCALL setSource(SignalDrop value) = 0;
      virtual ActiveSignal  BDAQCALL getEdge() = 0;
      virtual ErrorCode     BDAQCALL setEdge(ActiveSignal value) = 0;
      virtual double        BDAQCALL getLevel() = 0;
      virtual ErrorCode     BDAQCALL setLevel(double value) = 0;
      virtual TriggerAction BDAQCALL getAction() = 0;
      virtual ErrorCode     BDAQCALL setAction(TriggerAction value) = 0;
      virtual int32         BDAQCALL getDelayCount() = 0;
      virtual ErrorCode     BDAQCALL setDelayCount(int32 value) = 0;
   };

/* Interface PortDirection */
   class PortDirection
   {
   public:
      virtual int32      BDAQCALL getPort() = 0;
      virtual DioPortDir BDAQCALL getDirection() = 0;
      virtual ErrorCode  BDAQCALL setDirection(DioPortDir value) = 0;
   };

/* Interface NoiseFilterChannel */
   class NoiseFilterChannel
   {
   public:
      virtual int32     BDAQCALL getChannel() = 0;
      virtual bool      BDAQCALL getEnabled() = 0;
      virtual ErrorCode BDAQCALL setEnabled(bool value) = 0;
   };

/* Interface DiintChannel */
   class DiintChannel
   {
   public:
      virtual int32        BDAQCALL getChannel() = 0;
      virtual bool         BDAQCALL getEnabled() = 0;
      virtual ErrorCode    BDAQCALL setEnabled(bool value) = 0;
      virtual bool         BDAQCALL getGated() = 0;
      virtual ErrorCode    BDAQCALL setGated(bool value) = 0;
      virtual ActiveSignal BDAQCALL getTrigEdge() = 0;
      virtual ErrorCode    BDAQCALL setTrigEdge(ActiveSignal value) = 0;
   };

/* Interface DiCosintPort */
   class DiCosintPort
   {
   public:
      virtual int32     BDAQCALL getPort() = 0;
      virtual uint8     BDAQCALL getMask() = 0;
      virtual ErrorCode BDAQCALL setMask(uint8 value) = 0;
   };

/* Interface DiPmintPort */
   class DiPmintPort
   {
   public:
      virtual int32     BDAQCALL getPort() = 0;
      virtual uint8     BDAQCALL getMask() = 0;
      virtual ErrorCode BDAQCALL setMask(uint8 value) = 0;
      virtual uint8     BDAQCALL getPattern() = 0;
      virtual ErrorCode BDAQCALL setPattern(uint8 value) = 0;
   };

/* Interface DiPmintPort */
   class ScanPort
   {
   public:
      virtual int32     BDAQCALL getPortStart() = 0;
      virtual ErrorCode BDAQCALL setPortStart(int32 value) = 0;
      virtual int32     BDAQCALL getPortCount() = 0;
      virtual ErrorCode BDAQCALL setPortCount(int32 value) = 0;
      virtual int32     BDAQCALL getSamples() = 0;
      virtual ErrorCode BDAQCALL setSamples(int32 value) = 0;
      virtual int32     BDAQCALL getIntervalCount() = 0;
      virtual ErrorCode BDAQCALL setIntervalCount(int32 value) = 0;
   };

// ----------------------------------------------------------
// ctrl base class
// ----------------------------------------------------------
/* Interface DeviceCtrlBase */   
   class DeviceEventListener
   {
   public:
      virtual void BDAQCALL DeviceEvent(void * sender, DeviceEventArgs * args) = 0;
   };

   class DeviceCtrlBase
   {
   public:
      // method
      virtual void BDAQCALL Dispose() = 0; // destroy the instance
      virtual void BDAQCALL Cleanup() = 0; // release the resources allocated.
      virtual ErrorCode BDAQCALL UpdateProperties() = 0;

      // event
      virtual void BDAQCALL addRemovedListener(DeviceEventListener & listener) = 0;
      virtual void BDAQCALL removeRemovedListener(DeviceEventListener & listener) = 0;
      virtual void BDAQCALL addReconnectedListener(DeviceEventListener & listener) = 0;
      virtual void BDAQCALL removeReconnectedListener(DeviceEventListener & listener) = 0;
      virtual void BDAQCALL addPropertyChangedListener(DeviceEventListener & listener) = 0;
      virtual void BDAQCALL removePropertyChangedListener(DeviceEventListener & listener) = 0;

      // property
      virtual void                         BDAQCALL getSelectedDevice(DeviceInformation &x) = 0;
      virtual ErrorCode                    BDAQCALL setSelectedDevice(DeviceInformation const &x) = 0;
      virtual bool                         BDAQCALL getInitialized() = 0;
      virtual bool                         BDAQCALL getCanEditProperty() = 0;
      virtual HANDLE                       BDAQCALL getDevice() = 0;
      virtual HANDLE                       BDAQCALL getModule() = 0;
      virtual ICollection<DeviceTreeNode>* BDAQCALL getSupportedDevices() = 0;
      virtual ICollection<AccessMode>*     BDAQCALL getSupportedModes() = 0;
   };

   class DeviceCtrlBaseExt
   {
   public:
      // method
      virtual ErrorCode BDAQCALL ReadRegister(int32 startAddress, int32 length, void *data) = 0;
      virtual ErrorCode BDAQCALL WriteRegister(int32 startAddress, int32 length, void *data) = 0;

      virtual ErrorCode BDAQCALL ReadPrivateRegion(int32 signature, int32 length, uint8 *data) = 0;
      virtual ErrorCode BDAQCALL WritePrivateRegion(int32 signature, int32 length, uint8 *data) = 0;

      // property
      virtual ProductId           BDAQCALL getProductId() = 0;
      virtual int32               BDAQCALL getBoardId() = 0;
      virtual void                BDAQCALL getBoardVersion(int32 length, wchar_t *ver) = 0;
      virtual void                BDAQCALL getDriverVersion(int32 length, wchar_t *ver) = 0;
      virtual void                BDAQCALL getDllVersion(int32 length, wchar_t *ver) = 0;
      virtual void                BDAQCALL getLocation(int32 length, wchar_t *loc) = 0;
      virtual int32               BDAQCALL getPrivateRegionLength() = 0;
      virtual int32               BDAQCALL getHotResetPreventable() = 0;
      virtual ICollection<int32>* BDAQCALL getBaseAddresses() = 0;
      virtual ICollection<int32>* BDAQCALL getInterrupts() = 0;
      virtual ICollection<TerminalBoard>* BDAQCALL getSupportedTerminalBoard() = 0;
      virtual ICollection<EventId>*       BDAQCALL getSupportedEvents() = 0; 

      virtual TerminalBoard BDAQCALL getTerminalBoard() = 0;
      virtual ErrorCode     BDAQCALL setTerminalBoard(TerminalBoard board) = 0;
      virtual int32         BDAQCALL getLoadingTimeInit() = 0;
      virtual ErrorCode     BDAQCALL setLoadingTimeInit(int32 init) = 0;
   };

// ----------------------------------------------------------
// AI related classes
// ----------------------------------------------------------
/* Interface AiFeatures */ 
   typedef ICollection<AnalogInputChannel> AiChannelCollection;

   class AiFeatures
   {
   public:
      // ADC features
      virtual int32 BDAQCALL getResolution() = 0;
      virtual int32 BDAQCALL getDataSize() = 0;
      virtual int32 BDAQCALL getDataMask() = 0;

      // channel features
      virtual int32                        BDAQCALL getChannelCountMax() = 0;
      virtual AiChannelType                BDAQCALL getChannelType() = 0;
      virtual bool                         BDAQCALL getOverallValueRange() = 0;
      virtual bool                         BDAQCALL getThermoSupported() = 0;
      virtual ICollection<ValueRange>*     BDAQCALL getValueRanges() = 0;
      virtual ICollection<BurnoutRetType>* BDAQCALL getBurnoutReturnTypes() = 0;

      // CJC features
      virtual ICollection<int32>*         BDAQCALL getCjcChannels() = 0;

      // buffered ai->basic features
      virtual bool                        BDAQCALL getBufferedAiSupported() = 0;
      virtual SamplingMethod              BDAQCALL getSamplingMethod() = 0;
      virtual int32                       BDAQCALL getChannelStartBase() = 0;
      virtual int32                       BDAQCALL getChannelCountBase() = 0;

      // buffered ai->conversion clock features
      virtual ICollection<SignalDrop>*    BDAQCALL getConvertClockSources() = 0;
      virtual MathInterval                BDAQCALL getConvertClockRange() = 0;

      // buffered ai->burst scan
      virtual bool                        BDAQCALL getBurstScanSupported() = 0;
      virtual ICollection<SignalDrop>*    BDAQCALL getScanClockSources() = 0;
      virtual MathInterval                BDAQCALL getScanClockRange() = 0;
      virtual int32                       BDAQCALL getScanCountMax() = 0;

      // buffered ai->trigger features
      virtual bool                        BDAQCALL getTriggerSupported() = 0;
      virtual int32                       BDAQCALL getTriggerCount() = 0;
      virtual ICollection<SignalDrop>*    BDAQCALL getTriggerSources() = 0;
      virtual ICollection<TriggerAction>* BDAQCALL getTriggerActions() = 0;
      virtual MathInterval                BDAQCALL getTriggerDelayRange() = 0;

      // add trigger 1 features
      virtual bool                        BDAQCALL getTrigger1Supported() = 0;
      virtual ICollection<SignalDrop>*    BDAQCALL getTrigger1Sources() = 0;
      virtual ICollection<TriggerAction>* BDAQCALL getTrigger1Actions() = 0;
      virtual MathInterval                BDAQCALL getTrigger1DelayRange() = 0;

      // new: coupling & IEPE
      virtual ICollection<CouplingType> * BDAQCALL getCouplingTypes() = 0;
      virtual ICollection<IepeType> *     BDAQCALL getIepeTypes() = 0; 
   };

   class AiCtrlBase : public DeviceCtrlBase, public DeviceCtrlBaseExt
   {
   public:
      // property
      virtual AiFeatures*          BDAQCALL getFeatures() = 0;
      virtual AiChannelCollection* BDAQCALL getChannels() = 0;
      virtual int32                BDAQCALL getChannelCount() = 0;
   };

/* Interface InstantAiCtrl */
   class InstantAiCtrl : public AiCtrlBase
   {
   public:
      // method
      virtual ErrorCode BDAQCALL ReadAny(int32 chStart, int32 chCount, void *dataRaw, double *dataScaled) = 0;

      // property
      virtual CjcSetting* BDAQCALL getCjc() = 0;

      // helpers
      ErrorCode BDAQCALL Read(int32 ch, double &dataScaled)
      {
         return ReadAny(ch, 1, NULL, &dataScaled);
      }
      ErrorCode BDAQCALL Read(int32 ch, int16 &dataRaw)
      {
         return ReadAny(ch, 1, &dataRaw, NULL);
      }
      ErrorCode BDAQCALL Read(int32 ch, int32 &dataRaw)
      {
         return ReadAny(ch, 1, &dataRaw, NULL);
      }
      ErrorCode BDAQCALL Read(int32 chStart, int32 chCount, double dataScaled[])
      {
         return ReadAny(chStart, chCount, NULL, dataScaled);
      }
      ErrorCode BDAQCALL Read(int32 chStart, int32 chCount, int16 dataRaw[], double dataScaled[])
      {
         return ReadAny(chStart, chCount, dataRaw, dataScaled);
      }
      ErrorCode BDAQCALL Read(int32 chStart, int32 chCount, int32 dataRaw[], double dataScaled[])
      {
         return ReadAny(chStart, chCount, dataRaw, dataScaled);
      }
   };

/* Interface BufferedAiCtrl */
   class BfdAiEventListener
   {
   public:
      virtual void BDAQCALL BfdAiEvent(void * sender, BfdAiEventArgs * args) = 0;
   };

   class BufferedAiCtrl : public AiCtrlBase
   {
   public:
      // event
      virtual void BDAQCALL addDataReadyListener(BfdAiEventListener & listener) = 0;
      virtual void BDAQCALL removeDataReadyListener(BfdAiEventListener & listener) = 0;
      virtual void BDAQCALL addOverrunListener(BfdAiEventListener & listener) = 0;
      virtual void BDAQCALL removeOverrunListener(BfdAiEventListener & listener) = 0;
      virtual void BDAQCALL addCacheOverflowListener(BfdAiEventListener & listener) = 0;
      virtual void BDAQCALL removeCacheOverflowListener(BfdAiEventListener & listener) = 0;
      virtual void BDAQCALL addStoppedListener(BfdAiEventListener & listener) = 0;
      virtual void BDAQCALL removeStoppedListener(BfdAiEventListener & listener) = 0;

      // method
      virtual ErrorCode BDAQCALL Prepare() = 0;
      virtual ErrorCode BDAQCALL RunOnce() = 0;
      virtual ErrorCode BDAQCALL Start() = 0;
      virtual ErrorCode BDAQCALL Stop() = 0;
      virtual ErrorCode BDAQCALL GetDataI16(int32 count, int16 rawData[]) = 0;
      virtual ErrorCode BDAQCALL GetDataI32(int32 count, int32 rawData[]) = 0;
      virtual ErrorCode BDAQCALL GetDataF64(int32 count, double scaledData[]) = 0;
      virtual void      BDAQCALL Release() = 0;

      // property
      virtual void*         BDAQCALL getBuffer() = 0;
      virtual int32         BDAQCALL getBufferCapacity() = 0;
      virtual ControlState  BDAQCALL getState() =  0;
      virtual ScanChannel*  BDAQCALL getScanChannel() = 0;
      virtual ConvertClock* BDAQCALL getConvertClock() = 0;
      virtual ScanClock*    BDAQCALL getScanClock() = 0;
      virtual Trigger*      BDAQCALL getTrigger() = 0;
      virtual bool          BDAQCALL getStreaming() = 0;
      virtual ErrorCode     BDAQCALL setStreaming(bool value) = 0;

      // method
      virtual ErrorCode     BDAQCALL GetEventStatus(EventId id, int32 & status) = 0;

      // add trigger 1
      virtual Trigger*      BDAQCALL getTrigger1() = 0;
     
     // add event
      virtual void BDAQCALL addBurnOutListener(BfdAiEventListener & listener) = 0;
      virtual void BDAQCALL removeBurnOutListener(BfdAiEventListener & listener) = 0;
     
      // helpers
      ErrorCode BDAQCALL GetData(int32 count, int16 rawData[])
      {
         return GetDataI16(count, rawData);
      }
      ErrorCode BDAQCALL GetData(int32 count, int32 rawData[])
      {
         return GetDataI32(count, rawData);
      }
      ErrorCode BDAQCALL GetData(int32 count, double scaledData[])
      {
         return GetDataF64(count, scaledData);
      }
   };

// ----------------------------------------------------------
// AO related classes
// ----------------------------------------------------------
/* Interface AoFeatures */
   typedef ICollection<AnalogChannel> AoChannelCollection;

   class AoFeatures
   {
   public:
      // DAC features
      virtual int32 BDAQCALL getResolution() = 0;
      virtual int32 BDAQCALL getDataSize() = 0;
      virtual int32 BDAQCALL getDataMask() = 0;

      // channel features
      virtual int32                       BDAQCALL getChannelCountMax() = 0;
      virtual ICollection<ValueRange>*    BDAQCALL getValueRanges() = 0;
      virtual bool                        BDAQCALL getExternalRefAntiPolar() = 0;
      virtual MathInterval                BDAQCALL getExternalRefRange() = 0;

      // buffered ao->basic features
      virtual bool                        BDAQCALL getBufferedAoSupported() = 0;
      virtual SamplingMethod              BDAQCALL getSamplingMethod() = 0;
      virtual int32                       BDAQCALL getChannelStartBase() = 0;
      virtual int32                       BDAQCALL getChannelCountBase() = 0;

      // buffered ao->conversion clock features
      virtual ICollection<SignalDrop>*    BDAQCALL getConvertClockSources() = 0;
      virtual MathInterval                BDAQCALL getConvertClockRange() = 0;

      // buffered ao->trigger features
      virtual bool                        BDAQCALL getTriggerSupported() = 0;
      virtual int32                       BDAQCALL getTriggerCount() = 0;
      virtual ICollection<SignalDrop>*    BDAQCALL getTriggerSources() = 0;
      virtual ICollection<TriggerAction>* BDAQCALL getTriggerActions() = 0;
      virtual MathInterval                BDAQCALL getTriggerDelayRange() = 0;

      virtual bool                        BDAQCALL getTrigger1Supported() = 0;
      virtual ICollection<SignalDrop>*    BDAQCALL getTrigger1Sources() = 0;
      virtual ICollection<TriggerAction>* BDAQCALL getTrigger1Actions() = 0;
      virtual MathInterval                BDAQCALL getTrigger1DelayRange() = 0;
   };

/* Interface AoCtrlBase */
   class AoCtrlBase : public DeviceCtrlBase, public DeviceCtrlBaseExt
   {
   public:
      // property
      virtual AoFeatures*          BDAQCALL getFeatures() = 0;
      virtual AoChannelCollection* BDAQCALL getChannels() = 0;
      virtual int32                BDAQCALL getChannelCount() = 0;
      virtual double               BDAQCALL getExtRefValueForUnipolar() = 0;
      virtual ErrorCode            BDAQCALL setExtRefValueForUnipolar(double value) = 0;
      virtual double               BDAQCALL getExtRefValueForBipolar() = 0;
      virtual ErrorCode            BDAQCALL setExtRefValueForBipolar(double value) = 0;
   };

/* Interface InstantAoCtrl */
   class InstantAoCtrl : public AoCtrlBase
   {
   public:
      // method
      virtual ErrorCode BDAQCALL WriteAny(int32 chStart, int32 chCount, void *dataRaw, double *dataScaled) = 0;

      // helpers
      ErrorCode BDAQCALL Write(int32 ch, double dataScaled)
      {
         return WriteAny(ch, 1, NULL, &dataScaled);
      }
      ErrorCode BDAQCALL Write(int32 ch, int16 dataRaw)
      {
         return WriteAny(ch, 1, &dataRaw, NULL);
      }
      ErrorCode BDAQCALL Write(int32 ch, int32 dataRaw)
      {
         return WriteAny(ch, 1, &dataRaw, NULL);
      }
      ErrorCode BDAQCALL Write(int32 chStart, int32 chCount, double dataScaled[])
      {
         return WriteAny(chStart, chCount, NULL, dataScaled);
      }
      ErrorCode BDAQCALL Write(int32 chStart, int32 chCount, int16 dataRaw[])
      {
         return WriteAny(chStart, chCount, dataRaw, NULL);
      }
      ErrorCode BDAQCALL Write(int32 chStart, int32 chCount, int32 dataRaw[])
      {
         return WriteAny(chStart, chCount, dataRaw, NULL);
      }
   };

/* Interface BufferedAoCtrl */   
   class BfdAoEventListener
   {
   public:
      virtual void BDAQCALL BfdAoEvent(void * sender, BfdAoEventArgs * args) = 0;
   };

   class BufferedAoCtrl : public AoCtrlBase
   {
   public:
      // event
      virtual void BDAQCALL addDataTransmittedListener(BfdAoEventListener & listener) = 0;
      virtual void BDAQCALL removeDataTransmittedListener(BfdAoEventListener & listener) = 0;
      virtual void BDAQCALL addUnderrunListener(BfdAoEventListener & listener) = 0;
      virtual void BDAQCALL removeUnderrunListener(BfdAoEventListener & listener) = 0;
      virtual void BDAQCALL addCacheEmptiedListener(BfdAoEventListener & listener) = 0;
      virtual void BDAQCALL removeCacheEmptiedListener(BfdAoEventListener & listener) = 0;
      virtual void BDAQCALL addTransitStoppedListener(BfdAoEventListener & listener) = 0;
      virtual void BDAQCALL removeTransitStoppedListener(BfdAoEventListener & listener) = 0;
      virtual void BDAQCALL addStoppedListener(BfdAoEventListener & listener) = 0;
      virtual void BDAQCALL removeStoppedListener(BfdAoEventListener & listener) = 0;

      // method
      virtual ErrorCode BDAQCALL Prepare() = 0;
      virtual ErrorCode BDAQCALL RunOnce() = 0;
      virtual ErrorCode BDAQCALL Start() = 0;
      virtual ErrorCode BDAQCALL Stop(int32 action) = 0;
      virtual ErrorCode BDAQCALL SetDataI16(int32 count, int16 rawData[]) = 0;
      virtual ErrorCode BDAQCALL SetDataI32(int32 count, int32 rawData[]) = 0;
      virtual ErrorCode BDAQCALL SetDataF64(int32 count, double scaledData[]) = 0;
      virtual void      BDAQCALL Release() = 0;

      // property
      virtual void*         BDAQCALL getBuffer() = 0;
      virtual int32         BDAQCALL getBufferCapacity() = 0;
      virtual ControlState  BDAQCALL getState() =  0;
      virtual ScanChannel*  BDAQCALL getScanChannel() = 0;
      virtual ConvertClock* BDAQCALL getConvertClock() = 0;
      virtual Trigger*      BDAQCALL getTrigger() = 0;
      virtual bool          BDAQCALL getStreaming() = 0;
      virtual ErrorCode     BDAQCALL setStreaming(bool value) = 0;

      virtual Trigger*      BDAQCALL getTrigger1() = 0;

      // helpers
      ErrorCode BDAQCALL SetData(int32 count, int16 rawData[])
      {
         return SetDataI16(count, rawData);
      }
      ErrorCode BDAQCALL SetData(int32 count, int32 rawData[])
      {
         return SetDataI32(count, rawData);
      }
      ErrorCode BDAQCALL SetData(int32 count, double scaledData[])
      {
         return SetDataF64(count, scaledData);
      }
   };

// ----------------------------------------------------------
// DIO related classes
// ----------------------------------------------------------
/* Interface DioFeatures */ 
   class DioFeatures
   {
   public:
      // port features
      virtual bool                BDAQCALL getPortProgrammable() = 0;
      virtual int32               BDAQCALL getPortCount() = 0;
      virtual ICollection<uint8>* BDAQCALL getPortsType() = 0;
      virtual bool                BDAQCALL getDiSupported() = 0;
      virtual bool                BDAQCALL getDoSupported() = 0;

      // channel features
      virtual int32               BDAQCALL getChannelCountMax() = 0;
   };

/* Interface DioCtrlBase */ 
   class DioCtrlBase : public DeviceCtrlBase, public DeviceCtrlBaseExt
   {
   public:
      virtual int32 BDAQCALL getPortCount() = 0;
      virtual ICollection<PortDirection>* BDAQCALL getPortDirection() = 0;
   };

/* Interface DiFeatures */ 
   class DiFeatures : public DioFeatures
   {
   public:
      virtual ICollection<uint8>*         BDAQCALL getDataMask() = 0;

      // di noise filter features
      virtual bool                        BDAQCALL getNoiseFilterSupported() = 0;
      virtual ICollection<uint8>*         BDAQCALL getNoiseFilterOfChannels() = 0;
      virtual MathInterval                BDAQCALL getNoiseFilterBlockTimeRange() = 0;

      // di interrupt features
      virtual bool                        BDAQCALL getDiintSupported() = 0;
      virtual bool                        BDAQCALL getDiintGateSupported() = 0;
      virtual bool                        BDAQCALL getDiCosintSupported() = 0;
      virtual bool                        BDAQCALL getDiPmintSupported() = 0;
      virtual ICollection<ActiveSignal>*  BDAQCALL getDiintTriggerEdges() = 0;
      virtual ICollection<uint8>*         BDAQCALL getDiintOfChannels() = 0;
      virtual ICollection<uint8>*         BDAQCALL getDiintGateOfChannels() = 0;
      virtual ICollection<uint8>*         BDAQCALL getDiCosintOfPorts() = 0;
      virtual ICollection<uint8>*         BDAQCALL getDiPmintOfPorts() = 0;
      virtual ICollection<int32>*         BDAQCALL getSnapEventSources() = 0;

      // buffered di->basic features
      virtual bool                        BDAQCALL getBufferedDiSupported() = 0;
      virtual SamplingMethod              BDAQCALL getSamplingMethod() = 0;

      // buffered di->conversion clock features
      virtual ICollection<SignalDrop>*    BDAQCALL getConvertClockSources() = 0;
      virtual MathInterval                BDAQCALL getConvertClockRange() = 0;

      // buffered di->burst scan
      virtual bool                        BDAQCALL getBurstScanSupported() = 0;
      virtual ICollection<SignalDrop>*    BDAQCALL getScanClockSources() = 0;
      virtual MathInterval                BDAQCALL getScanClockRange() = 0;
      virtual int32                       BDAQCALL getScanCountMax() = 0;

      // buffered di->trigger features
      virtual bool                        BDAQCALL getTriggerSupported() = 0;
      virtual int32                       BDAQCALL getTriggerCount() = 0;
      virtual ICollection<SignalDrop>*    BDAQCALL getTriggerSources() = 0;
      virtual ICollection<TriggerAction>* BDAQCALL getTriggerActions() = 0;
      virtual MathInterval                BDAQCALL getTriggerDelayRange() = 0;
   };

/* Interface DiCtrlBase */ 
   class DiCtrlBase : public DioCtrlBase
   {
   public:
      virtual DiFeatures* BDAQCALL getFeatures() = 0;
      virtual ICollection<NoiseFilterChannel>* BDAQCALL getNoiseFilter() = 0;
   };

/* Interface InstantDiCtrl */ 
   class DiSnapEventListener
   {
   public:
      virtual void BDAQCALL DiSnapEvent(void * sender, DiSnapEventArgs * args) = 0;
   };

   class InstantDiCtrl : public DiCtrlBase
   {
   public:
      // event
      virtual void BDAQCALL addInterruptListener(DiSnapEventListener & listener) = 0;
      virtual void BDAQCALL removeInterruptListener(DiSnapEventListener & listener) = 0;
      virtual void BDAQCALL addChangeOfStateListener(DiSnapEventListener & listener) = 0;
      virtual void BDAQCALL removeChangeOfStateListener(DiSnapEventListener & listener) = 0;
      virtual void BDAQCALL addPatternMatchListener(DiSnapEventListener & listener) = 0;
      virtual void BDAQCALL removePatternMatchListener(DiSnapEventListener & listener) = 0;

      // method
      virtual ErrorCode BDAQCALL ReadAny(int32 portStart, int32 portCount, uint8 data[]) = 0;
      virtual ErrorCode BDAQCALL SnapStart() = 0;
      virtual ErrorCode BDAQCALL SnapStop() = 0;

      // property
      virtual ICollection<DiintChannel>* BDAQCALL getDiintChannels() = 0;
      virtual ICollection<DiCosintPort>* BDAQCALL getDiCosintPorts() = 0;
      virtual ICollection<DiPmintPort>*  BDAQCALL getDiPmintPorts() = 0;
     
      // new method
      virtual ErrorCode BDAQCALL ReadBit(int32 port, int32 bit, uint8* data) = 0;

      // new property
      virtual double    BDAQCALL getNoiseFilterBlockTime() = 0;
      virtual ErrorCode BDAQCALL setNoiseFilterBlockTime(double value) = 0;

      // helpers
      ErrorCode BDAQCALL Read(int32 port, uint8 & data)
      {
         return ReadAny(port, 1, &data);
      }
      ErrorCode BDAQCALL Read(int32 portStart, int32 portCount, uint8 data[])
      {
         return ReadAny(portStart, portCount, data);
      }

   };


/* Interface BufferedDiCtrl */
   class BfdDiEventListener
   {
   public:
      virtual void BDAQCALL BfdDiEvent(void * sender, BfdDiEventArgs * args) = 0;
   };

   class BufferedDiCtrl : public DiCtrlBase
   {
   public:
      // event
      virtual void BDAQCALL addDataReadyListener(BfdDiEventListener & listener) = 0;
      virtual void BDAQCALL removeDataReadyListener(BfdDiEventListener & listener) = 0;
      virtual void BDAQCALL addOverrunListener(BfdDiEventListener & listener) = 0;
      virtual void BDAQCALL removeOverrunListener(BfdDiEventListener & listener) = 0;
      virtual void BDAQCALL addCacheOverflowListener(BfdDiEventListener & listener) = 0;
      virtual void BDAQCALL removeCacheOverflowListener(BfdDiEventListener & listener) = 0;
      virtual void BDAQCALL addStoppedListener(BfdDiEventListener & listener) = 0;
      virtual void BDAQCALL removeStoppedListener(BfdDiEventListener & listener) = 0;

      // method
      virtual ErrorCode BDAQCALL Prepare() = 0;
      virtual ErrorCode BDAQCALL RunOnce() = 0;
      virtual ErrorCode BDAQCALL Start() = 0;
      virtual ErrorCode BDAQCALL Stop() = 0;
      virtual ErrorCode BDAQCALL GetData(int32 count, uint8 data[]) = 0;
      virtual void      BDAQCALL Release() = 0;

      // property
      virtual void*         BDAQCALL getBuffer() = 0;
      virtual int32         BDAQCALL getBufferCapacity() = 0;
      virtual ControlState  BDAQCALL getState() =  0;  
      virtual ScanPort*     BDAQCALL getScanPort() = 0;
      virtual ConvertClock* BDAQCALL getConvertClock() = 0;
      virtual ScanClock*    BDAQCALL getScanClock() = 0;
      virtual Trigger*      BDAQCALL getTrigger() = 0;
      virtual bool          BDAQCALL getStreaming() = 0;
      virtual ErrorCode     BDAQCALL setStreaming(bool value) = 0;
   };

/* Interface DoFeatures */ 
   class DoFeatures : public DioFeatures
   {
   public:
      virtual ICollection<uint8>*         BDAQCALL getDataMask() = 0;

      // do freeze features
      virtual ICollection<SignalDrop>*    BDAQCALL getDoFreezeSignalSources() = 0;

      // do reflect Wdt features
      virtual MathInterval                BDAQCALL getDoReflectWdtFeedIntervalRange() = 0;

      // buffered do->basic features
      virtual bool                        BDAQCALL getBufferedDoSupported() = 0;
      virtual SamplingMethod              BDAQCALL getSamplingMethod() = 0;

      // buffered do->conversion clock features
      virtual ICollection<SignalDrop>*    BDAQCALL getConvertClockSources() = 0;
      virtual MathInterval                BDAQCALL getConvertClockRange() = 0;

      // buffered do->burst scan
      virtual bool                        BDAQCALL getBurstScanSupported() = 0;
      virtual ICollection<SignalDrop>*    BDAQCALL getScanClockSources() = 0;
      virtual MathInterval                BDAQCALL getScanClockRange() = 0;
      virtual int32                       BDAQCALL getScanCountMax() = 0;

      // buffered do->trigger features
      virtual bool                        BDAQCALL getTriggerSupported() = 0;
      virtual int32                       BDAQCALL getTriggerCount() = 0;
      virtual ICollection<SignalDrop>*    BDAQCALL getTriggerSources() = 0;
      virtual ICollection<TriggerAction>* BDAQCALL getTriggerActions() = 0;
      virtual MathInterval                BDAQCALL getTriggerDelayRange() = 0;
   };

/* Interface DoCtrlBase */ 
   class DoCtrlBase : public DioCtrlBase
   {
   public:
      virtual DoFeatures* BDAQCALL getFeatures() = 0;
   };

/* Interface InstantDoCtrl */ 
   class InstantDoCtrl : public DoCtrlBase
   {
   public:
      // method
      virtual ErrorCode BDAQCALL WriteAny(int32 portStart, int32 portCount, uint8 data[]) = 0;
      virtual ErrorCode BDAQCALL ReadAny(int32 portStart, int32 portCount, uint8 data[]) = 0;
     virtual ErrorCode BDAQCALL WriteBit(int32 port, int32 bit, uint8 data) = 0;
     virtual ErrorCode BDAQCALL ReadBit(int32 port, int32 bit, uint8* data) = 0;

      // helpers
      ErrorCode BDAQCALL Write(int32 port, uint8 data)
      {
         return WriteAny(port, 1, &data);
      }
      ErrorCode BDAQCALL Write(int32 portStart, int32 portCount, uint8 data[])
      {
         return WriteAny(portStart, portCount, data);
      }
      ErrorCode BDAQCALL Read(int32 port, uint8 &data)
      {
         return ReadAny(port, 1, &data);
      }
      ErrorCode BDAQCALL Read(int32 portStart, int32 portCount, uint8 data[])
      {
         return ReadAny(portStart, portCount, data);
      }
   };

/* Interface BufferedDoCtrl */
   class BfdDoEventListener
   {
   public:
      virtual void BDAQCALL BfdDoEvent(void * sender, BfdDoEventArgs * args) = 0;
   };

   class BufferedDoCtrl : public DoCtrlBase
   {
   public:
      // event
      virtual void BDAQCALL addDataTransmittedListener(BfdDoEventListener & listener) = 0;
      virtual void BDAQCALL removeDataTransmittedListener(BfdDoEventListener & listener) = 0;
      virtual void BDAQCALL addUnderrunListener(BfdDoEventListener & listener) = 0;
      virtual void BDAQCALL removeUnderrunListener(BfdDoEventListener & listener) = 0;
      virtual void BDAQCALL addCacheEmptiedListener(BfdDoEventListener & listener) = 0;
      virtual void BDAQCALL removeCacheEmptiedListener(BfdDoEventListener & listener) = 0;
      virtual void BDAQCALL addTransitStoppedListener(BfdDoEventListener & listener) = 0;
      virtual void BDAQCALL removeTransitStoppedListener(BfdDoEventListener & listener) = 0;
      virtual void BDAQCALL addStoppedListener(BfdDoEventListener & listener) = 0;
      virtual void BDAQCALL removeStoppedListener(BfdDoEventListener & listener) = 0;

      // method
      virtual ErrorCode BDAQCALL Prepare() = 0;
      virtual ErrorCode BDAQCALL RunOnce() = 0;
      virtual ErrorCode BDAQCALL Start() = 0;
      virtual ErrorCode BDAQCALL Stop(int32 action) = 0;
      virtual ErrorCode BDAQCALL SetData(int32 count, uint8 data[]) = 0;
      virtual void      BDAQCALL Release() = 0;

      // property
      virtual void*         BDAQCALL getBuffer() = 0;
      virtual int32         BDAQCALL getBufferCapacity() = 0;
      virtual ControlState  BDAQCALL getState() =  0;
      virtual ScanPort*     BDAQCALL getScanPort() = 0;
      virtual ConvertClock* BDAQCALL getConvertClock() = 0;
      virtual Trigger*      BDAQCALL getTrigger() = 0;
      virtual bool          BDAQCALL getStreaming() = 0;
      virtual ErrorCode     BDAQCALL setStreaming(bool value) = 0;
   };

// ----------------------------------------------------------
// Counter related classes
// ----------------------------------------------------------
/* Interface CntrCtrlBase */ 
   class CntrEventListener
   {
   public:
      virtual void BDAQCALL CntrEvent(void * sender, CntrEventArgs * args) = 0;
   };

   class CounterCapabilityIndexer
   {
   public:
      virtual void  BDAQCALL Dispose() = 0;   // destroy the instance
      virtual int32 BDAQCALL getCount() = 0;
      virtual ICollection<CounterCapability>* BDAQCALL getItem(int32 channel) = 0;
   };

   class CntrFeatures 
   {
   public:
      // channel features
      virtual int32 BDAQCALL getChannelCountMax() = 0;
      virtual int32 BDAQCALL getResolution() = 0;
      virtual int32 BDAQCALL getDataSize() = 0;
      virtual CounterCapabilityIndexer* BDAQCALL getCapabilities() = 0;
   };

   class CntrFeaturesExt
   {
   public:
      // noise filter features
      virtual bool                BDAQCALL getNoiseFilterSupported() = 0;
      virtual ICollection<uint8>* BDAQCALL getNoiseFilterOfChannels() = 0;
      virtual MathInterval        BDAQCALL getNoiseFilterBlockTimeRange() = 0;
   };

   class CntrCtrlExt
   {
   public:
      virtual NoiseFilterChannel* BDAQCALL getNoiseFilter() = 0;

      // new property
      virtual double    BDAQCALL getNoiseFilterBlockTime() = 0;
      virtual ErrorCode BDAQCALL setNoiseFilterBlockTime(double value) = 0;
   };

   class CntrCtrlBase : public DeviceCtrlBase, public CntrCtrlExt, public DeviceCtrlBaseExt
   {
   public:
      // property
      virtual int32         BDAQCALL getChannel() = 0;
      virtual ErrorCode     BDAQCALL setChannel(int32 ch) = 0;
      virtual bool          BDAQCALL getEnabled() = 0;
      virtual ErrorCode     BDAQCALL setEnabled(bool enabled) = 0;
      virtual bool          BDAQCALL getRunning() = 0;
   };

/* Interface EventCounterCtrl */
   class EventCounterFeatures : public CntrFeatures, public CntrFeaturesExt
   {
      // No any other features at present for event counting.
   };

   class EventCounterCtrl : public CntrCtrlBase
   {
   public:
      // property
      virtual EventCounterFeatures* BDAQCALL getFeatures() = 0;
      virtual int32  BDAQCALL getValue() = 0;
   };

/* Interface FreqMeterCtrl */
   class FreqMeterFeatures : public CntrFeatures, public CntrFeaturesExt
   {
   public:
      virtual ICollection<FreqMeasureMethod>* BDAQCALL getFmMethods() = 0; 
   };

   class FreqMeterCtrl : public CntrCtrlBase
   {
   public:
      // property
      virtual FreqMeterFeatures*   BDAQCALL getFeatures() = 0;
      virtual double               BDAQCALL getValue() = 0;
      virtual FreqMeasureMethod    BDAQCALL getMethod() = 0;
      virtual ErrorCode            BDAQCALL setMethod(FreqMeasureMethod value) = 0;
      virtual double               BDAQCALL getCollectionPeriod() = 0;
      virtual ErrorCode            BDAQCALL setCollectionPeriod(double value) = 0;
   };

/* Interface OneShotCtrl */
   class OneShotFeatures : public CntrFeatures, public CntrFeaturesExt
   {
   public:
      virtual bool         BDAQCALL getOneShotEventSupported() = 0;
      virtual MathInterval BDAQCALL getDelayCountRange() = 0;
   };

   class OneShotCtrl : public CntrCtrlBase 
   {
   public:
      // event
      virtual void BDAQCALL addOneShotListener(CntrEventListener & listener) = 0;
      virtual void BDAQCALL removeOneShotListener(CntrEventListener & listener) = 0;

      // property
      virtual OneShotFeatures* BDAQCALL getFeatures() = 0;
      virtual int32            BDAQCALL getDelayCount() = 0;
      virtual ErrorCode        BDAQCALL setDelayCount(int32 value) = 0;
   };

/* Interface TimerPulseCtrl */
   class TimerPulseFeatures : public CntrFeatures, public CntrFeaturesExt
   {
   public:
      virtual MathInterval BDAQCALL getTimerFrequencyRange() = 0;
      virtual bool         BDAQCALL getTimerEventSupported() = 0;
   };

   class TimerPulseCtrl : public CntrCtrlBase
   {
   public:
      // event
      virtual void BDAQCALL addTimerTickListener(CntrEventListener & listener) = 0;
      virtual void BDAQCALL removeTimerTickListener(CntrEventListener & listener) = 0;

      // property
      virtual TimerPulseFeatures* BDAQCALL getFeatures() = 0;
      virtual double              BDAQCALL getFrequency() = 0;
      virtual ErrorCode           BDAQCALL setFrequency(double value) = 0;
   };

/* Interface PwMeterCtrl */
   class PwMeterFeatures : public CntrFeatures, public CntrFeaturesExt
   {
   public:
      virtual ICollection<CounterCascadeGroup>* BDAQCALL getPwmCascadeGroup() = 0;
      virtual bool BDAQCALL getOverflowEventSupported() = 0;
   };

   class PwMeterCtrl : public CntrCtrlBase
   {
   public:
      // event
      virtual void BDAQCALL addOverflowListener(CntrEventListener & listener) = 0;
      virtual void BDAQCALL removeOverflowListener(CntrEventListener & listener) = 0;

      // property
      virtual PwMeterFeatures* BDAQCALL getFeatures() = 0;
      virtual void BDAQCALL getValue(PulseWidth &width) = 0;  
   };

/* Interface PwModulatorCtrl */
   class PwModulatorFeatures : public CntrFeatures, public CntrFeaturesExt
   {
   public:
      virtual MathInterval BDAQCALL getHiPeriodRange() = 0;
      virtual MathInterval BDAQCALL getLoPeriodRange() = 0;
   };

   class PwModulatorCtrl : public CntrCtrlBase
   {
   public:
      // property
      virtual PwModulatorFeatures* BDAQCALL getFeatures() = 0;
      virtual void                 BDAQCALL getPulseWidth(PulseWidth &width) = 0;
      virtual ErrorCode            BDAQCALL setPulseWidth(PulseWidth const &width) = 0;
   };

/* Interface UdCounterCtrl */
   class UdCntrEventListener
   {
   public:
      virtual void BDAQCALL UdCntrEvent(void * sender, UdCntrEventArgs * args) = 0;
   };

   class UdCounterFeatures : public CntrFeatures, public CntrFeaturesExt
   {
   public:
      virtual ICollection<SignalCountingType>* BDAQCALL getCountingTypes() = 0; 
      virtual ICollection<int32>*              BDAQCALL getInitialValues() = 0;
      virtual ICollection<int32>*              BDAQCALL getSnapEventSources() = 0;
   };

   class UdCounterCtrl : public CntrCtrlBase
   {
   public:
      // event
      virtual void BDAQCALL addUdCntrEventListener(UdCntrEventListener &listener) = 0;
      virtual void BDAQCALL removeUdCntrEventListener(UdCntrEventListener &listener) = 0;

      // method
      virtual ErrorCode BDAQCALL SnapStart(int32 srcId) = 0;
      virtual ErrorCode BDAQCALL SnapStop(int32 srcId) = 0;
      virtual ErrorCode BDAQCALL CompareSetTable(int32 count, int32 *table) = 0;
      virtual ErrorCode BDAQCALL CompareSetInterval(int32 start, int32 increment,int32 count) = 0;
      virtual ErrorCode BDAQCALL CompareClear() = 0; 
      virtual ErrorCode BDAQCALL ValueReset() = 0;

      // property
      virtual UdCounterFeatures* BDAQCALL getFeatures() = 0;
      virtual int32              BDAQCALL getValue() = 0;
      virtual SignalCountingType BDAQCALL getCountingType() = 0;
      virtual ErrorCode          BDAQCALL setCountingType(SignalCountingType value) = 0;
      virtual int32              BDAQCALL getInitialValue() = 0;
      virtual ErrorCode          BDAQCALL setInitialValue(int32 value) = 0;
      virtual int32              BDAQCALL getResetTimesByIndex() = 0;
      virtual ErrorCode          BDAQCALL setResetTimesByIndex(int32 value) = 0;
   };

#else /* C style interface */
   // ----------------------------------------------------------
   // common classes
   // ----------------------------------------------------------
   typedef struct ICollection          ICollection;
   typedef struct AnalogChannel        AnalogChannel;
   typedef struct AnalogInputChannel   AnalogInputChannel;
   typedef struct CjcSetting           CjcSetting;
   typedef struct ScanChannel          ScanChannel;
   typedef struct ConvertClock         ConvertClock;
   typedef struct ScanClock            ScanClock;
   typedef struct Trigger              Trigger;
   typedef struct PortDirection        PortDirection;
   typedef struct NoiseFilterChannel   NoiseFilterChannel;
   typedef struct DiintChannel         DiintChannel;
   typedef struct DiCosintPort         DiCosintPort;
   typedef struct DiPmintPort          DiPmintPort;
   typedef struct ScanPort             ScanPort;

   typedef struct DeviceEventHandler {
      void (BDAQCALL *DeviceEvent)(void *_this, void *sender, DeviceEventArgs *args);
   } DeviceEventHandler;

   typedef struct DeviceEventListener {
      DeviceEventHandler const *vtbl;
   }DeviceEventListener;

   // ----------------------------------------------------------
   // AI related classes
   // ----------------------------------------------------------
   typedef struct BfdAiEventHandler {
      void (BDAQCALL *BfdAiEvent)(void *_this, void *sender, BfdAiEventArgs *args);
   } BfdAiEventHandler;

   typedef struct BfdAiEventListener {
      BfdAiEventHandler const *vtbl;
   } BfdAiEventListener;

   typedef struct AiFeatures        AiFeatures;
   typedef struct InstantAiCtrl     InstantAiCtrl;
   typedef struct BufferedAiCtrl    BufferedAiCtrl;

   // ----------------------------------------------------------
   // AO related classes
   // ----------------------------------------------------------
   typedef struct BfdAoEventHandler {
      void (BDAQCALL *BfdAoEvent)(void *_this, void *sender, BfdAoEventArgs *args);
   } BfdAoEventHandler;

   typedef struct BfdAoEventListener {
      BfdAoEventHandler const *vtbl;
   } BfdAoEventListener;

   typedef struct AoFeatures        AoFeatures;
   typedef struct InstantAoCtrl     InstantAoCtrl;
   typedef struct BufferedAoCtrl    BufferedAoCtrl;

   // ----------------------------------------------------------
   // DIO related classes
   // ----------------------------------------------------------
   typedef struct DiSnapEventHandler {
      void (BDAQCALL *DiSnapEvent)(void *_this, void *sender, DiSnapEventArgs *args);
   } DiSnapEventHandler;

   typedef struct DiSnapEventListener {
      DiSnapEventHandler const *vtbl;
   } DiSnapEventListener;

   typedef struct BfdDiEventHandler {
      void (BDAQCALL *BfdDiEvent)(void *_this, void *sender, BfdDiEventArgs *args);
   } BfdDiEventHandler;

   typedef struct BfdDiEventListener {
      BfdDiEventHandler const *vtbl;
   } BfdDiEventListener;

   typedef struct DiFeatures        DiFeatures;
   typedef struct InstantDiCtrl     InstantDiCtrl;
   typedef struct InstantDoCtrl     InstantDoCtrl;

   typedef struct BfdDoEventHandler {
      void (BDAQCALL *BfdDoEvent)(void *_this, void *sender, BfdDoEventArgs *args);
   } BfdDoEventHandler;

   typedef struct BfdDoEventListener {
      BfdDoEventHandler const *vtbl;
   } BfdDoEventListener;

   typedef struct DoFeatures        DoFeatures;
   typedef struct BufferedDiCtrl    BufferedDiCtrl;
   typedef struct BufferedDoCtrl    BufferedDoCtrl;

   // ----------------------------------------------------------
   // Counter related classes
   // ----------------------------------------------------------
   typedef struct CntrEventHandler {
      void (BDAQCALL *CntrEvent)(void *_this, void *sender, CntrEventArgs *args);
   } CntrEventHandler;

   typedef struct CntrEventListener {
      CntrEventHandler const *vtbl;
   } CntrEventListener;

   typedef struct CounterCapabilityIndexer CounterCapabilityIndexer;

   typedef struct EventCounterFeatures EventCounterFeatures;
   typedef struct EventCounterCtrl     EventCounterCtrl;

   typedef struct FreqMeterFeatures    FreqMeterFeatures;
   typedef struct FreqMeterCtrl        FreqMeterCtrl;

   typedef struct OneShotFeatures      OneShotFeatures;
   typedef struct OneShotCtrl          OneShotCtrl;

   typedef struct TimerPulseFeatures   TimerPulseFeatures;
   typedef struct TimerPulseCtrl       TimerPulseCtrl;

   typedef struct PwMeterFeatures      PwMeterFeatures;
   typedef struct PwMeterCtrl          PwMeterCtrl;

   typedef struct PwModulatorFeatures  PwModulatorFeatures;
   typedef struct PwModulatorCtrl      PwModulatorCtrl;

   typedef struct UdCntrEventHandler {
      void (BDAQCALL *UdCntrEvent)(void *_this, void *sender, UdCntrEventArgs *args);
   } UdCntrEventHandler;

   typedef struct UdCntrEventListener {
      UdCntrEventHandler const *vtbl;
   } UdCntrEventListener;

   typedef struct UdCounterFeatures    UdCounterFeatures;
   typedef struct UdCounterCtrl        UdCounterCtrl;

#endif

// **********************************************************
// factory method define
// **********************************************************
#ifndef _BIONIC_DAQ_DLL

#  if defined(_WIN32) || defined(WIN32)
   // the following two methods are for internal using only, don't call them directly!
   __inline HMODULE GetBDaqLibInstance()
   {
      static HMODULE instance = NULL;
      if (instance == NULL) { instance = LoadLibrary(TEXT("biodaq.dll")); }
      return instance;
   }
   __inline FARPROC GetBDaqApiAddress(char const * name)
   {
   #ifdef _WIN32_WCE
      return GetProcAddressA(GetBDaqLibInstance(), name);
   #else
      return GetProcAddress(GetBDaqLibInstance(), name);
   #endif
   }

#  if !defined(__cplusplus) || defined(_BDAQ_C_INTERFACE) // ANSI-C INTERFACE
#  include <assert.h>
   __inline FARPROC ** BDAQ_CSCL_ANSI_C_Table()
   {
      static FARPROC * ansi_c_table = NULL;
      return &ansi_c_table;
   }
   __inline void BDAQ_CSCL_ANSI_C_Init()
   {
      FARPROC ** tablePtr = BDAQ_CSCL_ANSI_C_Table();
      if (*tablePtr == NULL) {
         *tablePtr = (FARPROC *)GetBDaqApiAddress("BDAQ_CSCL_ANSI_C_APIs");
      }
      assert (*tablePtr != NULL);
   }
#  else
#  define BDAQ_CSCL_ANSI_C_Init()  do{}while(0)
#  endif

   __inline void* BDaqObjectCreate(char const * creator)
   {
      BDAQ_CSCL_ANSI_C_Init();
      {
      void*(BDAQCALL *fn)() = (void*(BDAQCALL *)())GetBDaqApiAddress(creator);
      return fn();
      }
   }

   // Global APIs
   __inline ErrorCode AdxDeviceGetLinkageInfo(
      int32   deviceParent,    /*IN*/
      int32   index,           /*IN*/
      int32   *deviceNumber,   /*OUT*/
      wchar_t *description,    /*OUT OPTIONAL*/
      int32   *subDeviceCount) /*OUT OPTIONAL*/
   {
      BDAQ_CSCL_ANSI_C_Init();
      {
      typedef ErrorCode (BDAQCALL *PfnGetLinkageInfo)(int32,int32,int32*,wchar_t*,int32*);
      PfnGetLinkageInfo fn = (PfnGetLinkageInfo)GetBDaqApiAddress("AdxDeviceGetLinkageInfo");
      return fn ? fn(deviceParent, index, deviceNumber, description, subDeviceCount) : ErrorDriverNotFound;
      }
   }

   __inline ErrorCode AdxGetValueRangeInformation(
      ValueRange   type,         /*IN*/
      int32        descBufSize,  /*IN*/
      wchar_t      *description, /*OUT OPTIONAL*/
      MathInterval *range,       /*OUT OPTIONAL*/
      ValueUnit    *unit)        /*OUT OPTIONAL */
   {
      BDAQ_CSCL_ANSI_C_Init();
      {
      typedef ErrorCode (BDAQCALL *PfnGetVrgInfo)(int32,int32,wchar_t*,MathInterval*,int32*);
      PfnGetVrgInfo fn = (PfnGetVrgInfo)GetBDaqApiAddress("AdxGetValueRangeInformation");
      return fn ? fn(type, descBufSize, description, range, (int32*)unit) : ErrorDriverNotFound;
      }
   }

   __inline ErrorCode AdxGetSignalConnectionInformation(
      SignalDrop     signal,      /*IN*/
      int32          descBufSize, /*IN*/
      wchar_t        *description,/*OUT OPTIONAL*/
      SignalPosition *position)   /*OUT OPTIONAL*/
   {
      BDAQ_CSCL_ANSI_C_Init();
      {
      typedef ErrorCode (BDAQCALL *PfnGetSignalCnntInfo)(int32,int32,wchar_t*,int32*);
      PfnGetSignalCnntInfo fn = (PfnGetSignalCnntInfo)GetBDaqApiAddress("AdxGetSignalConnectionInformation");
      return fn ? fn(signal, descBufSize, description, (int32*)position) : ErrorDriverNotFound;
      }
   }

   __inline ErrorCode AdxEnumToString(
      wchar_t const *enumTypeName,    /*IN*/
      int32         enumValue,        /*IN*/
      int32         enumStringLength, /*IN*/
      wchar_t       *enumString)      /*OUT*/
   {
      BDAQ_CSCL_ANSI_C_Init();
      {
      typedef ErrorCode (BDAQCALL *PfnEnumToStr)(wchar_t const*,int32,int32,wchar_t*);
      PfnEnumToStr fn = (PfnEnumToStr)GetBDaqApiAddress("AdxEnumToString");
      return fn ? fn(enumTypeName, enumValue, enumStringLength, enumString) : ErrorDriverNotFound;
      }
   }
   
   __inline ErrorCode AdxStringToEnum(
      wchar_t const *enumTypeName,    /*IN*/
      wchar_t const *enumString,      /*IN*/
      int32         *enumValue)       /*OUT*/
   {
      BDAQ_CSCL_ANSI_C_Init();
      {
      typedef ErrorCode (BDAQCALL *PfnStrToEnum)(wchar_t const*,wchar_t const*,int32*);
      PfnStrToEnum fn = (PfnStrToEnum)GetBDaqApiAddress("AdxStringToEnum");
      return fn ? fn(enumTypeName, enumString, enumValue) : ErrorDriverNotFound;
      }
   }

   // Biodaq object create methods
   __inline InstantAiCtrl* AdxInstantAiCtrlCreate()
   {
      return (InstantAiCtrl*)BDaqObjectCreate("AdxInstantAiCtrlCreate");
   }
   __inline BufferedAiCtrl* AdxBufferedAiCtrlCreate()
   {
      return (BufferedAiCtrl*)BDaqObjectCreate("AdxBufferedAiCtrlCreate");
   }

   __inline InstantAoCtrl* AdxInstantAoCtrlCreate()
   {
      return (InstantAoCtrl*)BDaqObjectCreate("AdxInstantAoCtrlCreate");
   }
   __inline BufferedAoCtrl* AdxBufferedAoCtrlCreate()
   {
      return (BufferedAoCtrl*)BDaqObjectCreate("AdxBufferedAoCtrlCreate");
   }

   __inline InstantDiCtrl* AdxInstantDiCtrlCreate()
   {
      return (InstantDiCtrl*)BDaqObjectCreate("AdxInstantDiCtrlCreate");
   }
   __inline BufferedDiCtrl* AdxBufferedDiCtrlCreate()
   {
      return (BufferedDiCtrl*)BDaqObjectCreate("AdxBufferedDiCtrlCreate");
   }

   __inline InstantDoCtrl* AdxInstantDoCtrlCreate()
   {
      return (InstantDoCtrl*)BDaqObjectCreate("AdxInstantDoCtrlCreate");
   }
   __inline BufferedDoCtrl* AdxBufferedDoCtrlCreate()
   {
      return (BufferedDoCtrl*)BDaqObjectCreate("AdxBufferedDoCtrlCreate");
   }

   __inline EventCounterCtrl* AdxEventCounterCtrlCreate()
   {
      return (EventCounterCtrl*)BDaqObjectCreate("AdxEventCounterCtrlCreate");
   }

   __inline FreqMeterCtrl* AdxFreqMeterCtrlCreate()
   {
      return (FreqMeterCtrl*)BDaqObjectCreate("AdxFreqMeterCtrlCreate");
   }

   __inline OneShotCtrl* AdxOneShotCtrlCreate()
   {
      return (OneShotCtrl*)BDaqObjectCreate("AdxOneShotCtrlCreate");
   }

   __inline PwMeterCtrl* AdxPwMeterCtrlCreate()
   {
      return (PwMeterCtrl*)BDaqObjectCreate("AdxPwMeterCtrlCreate");
   }

   __inline PwModulatorCtrl* AdxPwModulatorCtrlCreate()
   {
      return (PwModulatorCtrl*)BDaqObjectCreate("AdxPwModulatorCtrlCreate");
   }

   __inline TimerPulseCtrl* AdxTimerPulseCtrlCreate()
   {
      return (TimerPulseCtrl*)BDaqObjectCreate("AdxTimerPulseCtrlCreate");
   }

   __inline UdCounterCtrl* AdxUdCounterCtrlCreate()
   {
      return (UdCounterCtrl*)BDaqObjectCreate("AdxUdCounterCtrlCreate");
   }

#  if !defined(__cplusplus) || defined(_BDAQ_C_INTERFACE) // ANSI-C INTERFACE
#  define bdaq_obj_func(index, type)        (type (*BDAQ_CSCL_ANSI_C_Table())[index])
#  define bdaq_obj_set(index, vt)           ((ErrorCode (BDAQCALL *)(void *, vt))(*BDAQ_CSCL_ANSI_C_Table())[index])
#  define bdaq_obj_get(index, rt)           ((rt (BDAQCALL *)(void *))(*BDAQ_CSCL_ANSI_C_Table())[index])
#  define bdaq_obj_get_v1(index, rt, vt)    ((rt (BDAQCALL *)(void *, vt))(*BDAQ_CSCL_ANSI_C_Table())[index])

   // ----------------------------------------------------------
   // common classes : ICollection (method index: 0~2)
   // ----------------------------------------------------------
   __inline void  ICollection_Dispose(ICollection *_this)              { bdaq_obj_func(0, (void (BDAQCALL *)(void *)))(_this);  }
   __inline int32 ICollection_getCount(ICollection *_this)             { return bdaq_obj_get(1, int32)(_this);                  }
   __inline void* ICollection_getItem(ICollection *_this, int32 index) { return bdaq_obj_get_v1(2, void *, int32)(_this, index);}

   // ----------------------------------------------------------
   // common classes : AnalogChannel (method index: 3~5)
   // ----------------------------------------------------------
   __inline int32      AnalogChannel_getChannel(AnalogChannel *_this)                      { return bdaq_obj_get(3, int32)(_this);            }
   __inline ValueRange AnalogChannel_getValueRange(AnalogChannel *_this)                   { return bdaq_obj_get(4, ValueRange)(_this);       }
   __inline ErrorCode  AnalogChannel_setValueRange(AnalogChannel *_this, ValueRange value) { return bdaq_obj_set(5, ValueRange)(_this, value);}

   // ----------------------------------------------------------
   // common classes : AnalogInputChannel (method index: 6~14)
   // ----------------------------------------------------------
   __inline int32          AnalogInputChannel_getChannel(AnalogInputChannel *_this)                              { return bdaq_obj_get(6, int32)(_this);                  } 
   __inline ValueRange     AnalogInputChannel_getValueRange(AnalogInputChannel *_this)                           { return bdaq_obj_get(7, ValueRange)(_this);             }
   __inline ErrorCode      AnalogInputChannel_setValueRange(AnalogInputChannel *_this, ValueRange value)         { return bdaq_obj_set(8, ValueRange)(_this, value);      }
   __inline AiSignalType   AnalogInputChannel_getSignalType(AnalogInputChannel *_this)                           { return bdaq_obj_get(9, AiSignalType)(_this);           }
   __inline ErrorCode      AnalogInputChannel_setSignalType(AnalogInputChannel *_this, AiSignalType value)       { return bdaq_obj_set(10, AiSignalType)(_this, value);   }
   __inline BurnoutRetType AnalogInputChannel_getBurnoutRetType(AnalogInputChannel *_this)                       { return bdaq_obj_get(11, BurnoutRetType)(_this);        }
   __inline ErrorCode      AnalogInputChannel_setBurnoutRetType(AnalogInputChannel *_this, BurnoutRetType value) { return bdaq_obj_set(12, BurnoutRetType)(_this, value); }
   __inline double         AnalogInputChannel_getBurnoutRetValue(AnalogInputChannel *_this)                      { return bdaq_obj_get(13, double)(_this);                }
   __inline ErrorCode      AnalogInputChannel_setBurnoutRetValue(AnalogInputChannel *_this, double value)        { return bdaq_obj_set(14, double)(_this, value);         }
   // New: Coupling & IEPE
   __inline CouplingType   AnalogInputChannel_getCouplingType(AnalogInputChannel *_this)                         { return bdaq_obj_get(735, CouplingType)(_this);         }
   __inline ErrorCode      AnalogInputChannel_setCouplingType(AnalogInputChannel *_this, CouplingType value)     { return bdaq_obj_set(736, CouplingType)(_this, value);  }
   __inline IepeType       AnalogInputChannel_getIepeType(AnalogInputChannel *_this)                             { return bdaq_obj_get(737, IepeType)(_this);             }
   __inline ErrorCode      AnalogInputChannel_setIepeType(AnalogInputChannel *_this, IepeType value)             { return bdaq_obj_set(738, IepeType)(_this, value);      }
   
   // ----------------------------------------------------------
   // common classes : CjcSetting (method index: 15~18)
   // ----------------------------------------------------------
   __inline int32      CjcSetting_getChannel(CjcSetting *_this)               { return bdaq_obj_get(15, int32)(_this);         }
   __inline ErrorCode  CjcSetting_setChannel(CjcSetting *_this, int32 ch)     { return bdaq_obj_set(16, int32)(_this, ch);     }
   __inline double     CjcSetting_getValue(CjcSetting *_this)                 { return bdaq_obj_get(17, double)(_this);        }
   __inline ErrorCode  CjcSetting_setValue(CjcSetting *_this, double value)   { return bdaq_obj_set(18, double)(_this, value); }

   // ----------------------------------------------------------
   // common classes : ScanChannel (method index: 19~26)
   // ----------------------------------------------------------
   __inline int32      ScanChannel_getChannelStart(ScanChannel *_this)               { return bdaq_obj_get(19, int32)(_this);         }
   __inline ErrorCode  ScanChannel_setChannelStart(ScanChannel *_this, int32 value)  { return bdaq_obj_set(20, int32)(_this, value);  }
   __inline int32      ScanChannel_getChannelCount(ScanChannel *_this)               { return bdaq_obj_get(21, int32)(_this);         }
   __inline ErrorCode  ScanChannel_setChannelCount(ScanChannel *_this, int32 value)  { return bdaq_obj_set(22, int32)(_this, value);  }
   __inline int32      ScanChannel_getSamples(ScanChannel *_this)                    { return bdaq_obj_get(23, int32)(_this);         }
   __inline ErrorCode  ScanChannel_setSamples(ScanChannel *_this, int32 value)       { return bdaq_obj_set(24, int32)(_this, value);  }
   __inline int32      ScanChannel_getIntervalCount(ScanChannel *_this)              { return bdaq_obj_get(25, int32)(_this);         }
   __inline ErrorCode  ScanChannel_setIntervalCount(ScanChannel *_this, int32 value) { return bdaq_obj_set(26, int32)(_this, value);  }

   // ----------------------------------------------------------
   // common classes : ConvertClock (method index: 27~30)
   // ----------------------------------------------------------
   __inline SignalDrop ConvertClock_getSource(ConvertClock *_this)                   { return bdaq_obj_get(27, SignalDrop)(_this);       }
   __inline ErrorCode  ConvertClock_setSource(ConvertClock *_this, SignalDrop value) { return bdaq_obj_set(28, SignalDrop)(_this, value);}
   __inline double     ConvertClock_getRate(ConvertClock *_this)                     { return bdaq_obj_get(29, double)(_this);           }
   __inline ErrorCode  ConvertClock_setRate(ConvertClock *_this, double value)       { return bdaq_obj_set(30, double)(_this, value);    }

   // ----------------------------------------------------------
   // common classes : ScanClock (method index: 31~36)
   // ----------------------------------------------------------
   __inline SignalDrop ScanClock_getSource(ScanClock *_this)                   { return bdaq_obj_get(31, SignalDrop)(_this);       }
   __inline ErrorCode  ScanClock_setSource(ScanClock *_this, SignalDrop value) { return bdaq_obj_set(32, SignalDrop)(_this, value);}
   __inline double     ScanClock_getRate(ScanClock *_this)                     { return bdaq_obj_get(33, double)(_this);           }
   __inline ErrorCode  ScanClock_setRate(ScanClock *_this, double value)       { return bdaq_obj_set(34, double)(_this, value);    }
   __inline int32      ScanClock_getScanCount(ScanClock *_this)                { return bdaq_obj_get(35, int32)(_this);            }
   __inline ErrorCode  ScanClock_setScanCount(ScanClock *_this, int32 value)   { return bdaq_obj_set(36, int32)(_this, value);     }

   // ----------------------------------------------------------
   // common classes : Trigger (method index: 37~46)
   // ----------------------------------------------------------
   __inline SignalDrop     Trigger_getSource(Trigger *_this)                     { return bdaq_obj_get(37, SignalDrop)(_this);          }
   __inline ErrorCode      Trigger_setSource(Trigger *_this,SignalDrop value)    { return bdaq_obj_set(38, SignalDrop)(_this, value);   }
   __inline ActiveSignal   Trigger_getEdge(Trigger *_this)                       { return bdaq_obj_get(39, ActiveSignal)(_this);        }
   __inline ErrorCode      Trigger_setEdge(Trigger *_this, ActiveSignal value)   { return bdaq_obj_set(40, ActiveSignal)(_this, value); }
   __inline double         Trigger_getLevel(Trigger *_this)                      { return bdaq_obj_get(41, double)(_this);              }
   __inline ErrorCode      Trigger_setLevel(Trigger *_this, double value)        { return bdaq_obj_set(42, double)(_this, value);       }
   __inline TriggerAction  Trigger_getAction(Trigger *_this)                     { return bdaq_obj_get(43, TriggerAction)(_this);       }
   __inline ErrorCode      Trigger_setAction(Trigger *_this, TriggerAction value){ return bdaq_obj_set(44, TriggerAction)(_this, value);}
   __inline int32          Trigger_getDelayCount(Trigger *_this)                 { return bdaq_obj_get(45, int32)(_this);               }
   __inline ErrorCode      Trigger_setDelayCount(Trigger *_this, int32 value)    { return bdaq_obj_set(46, int32)(_this, value);        }

   // ----------------------------------------------------------
   // common classes : PortDirection (method index: 47~49)
   // ----------------------------------------------------------
   __inline int32       PortDirection_getPort(PortDirection *_this)                       { return bdaq_obj_get(47, int32)(_this);            }
   __inline DioPortDir  PortDirection_getDirection(PortDirection *_this)                  { return bdaq_obj_get(48, DioPortDir)(_this);       }
   __inline ErrorCode   PortDirection_setDirection(PortDirection *_this, DioPortDir value){ return bdaq_obj_set(49, DioPortDir)(_this, value);}

   // ----------------------------------------------------------
   // common classes : NoiseFilterChannel (method index: 50~52)
   // ----------------------------------------------------------
   __inline int32      NoiseFilterChannel_getChannel(NoiseFilterChannel *_this)            { return bdaq_obj_get(50, int32)(_this);      }
   __inline int8       NoiseFilterChannel_getEnabled(NoiseFilterChannel *_this)            { return bdaq_obj_get(51, int8)(_this);       }
   __inline ErrorCode  NoiseFilterChannel_setEnabled(NoiseFilterChannel *_this, int8 value){ return bdaq_obj_set(52, int8)(_this, value);}

   // ----------------------------------------------------------
   // common classes : DiintChannel (method index: 53~59)
   // ----------------------------------------------------------
   __inline int32         DiintChannel_getChannel(DiintChannel *_this)                     { return bdaq_obj_get(53, int32)(_this);              }
   __inline int8          DiintChannel_getEnabled(DiintChannel *_this)                     { return bdaq_obj_get(54, int8)(_this);               }
   __inline ErrorCode     DiintChannel_setEnabled(DiintChannel *_this, int8 value)         { return bdaq_obj_set(55, int8)(_this, value);        }
   __inline int8          DiintChannel_getGated(DiintChannel *_this)                       { return bdaq_obj_get(56, int8)(_this);               }
   __inline ErrorCode     DiintChannel_setGated(DiintChannel *_this, int8 value)           { return bdaq_obj_set(57, int8)(_this, value);        }
   __inline ActiveSignal  DiintChannel_getTrigEdge(DiintChannel *_this)                    { return bdaq_obj_get(58, ActiveSignal)(_this);       }
   __inline ErrorCode     DiintChannel_setTrigEdge(DiintChannel *_this, ActiveSignal value){ return bdaq_obj_set(59, ActiveSignal)(_this, value);}

   // ----------------------------------------------------------
   // common classes : DiCosintPort (method index: 60~62)
   // ----------------------------------------------------------
   __inline int32      DiCosintPort_getPort(DiCosintPort *_this)               { return bdaq_obj_get(60, int32)(_this);         }
   __inline uint8      DiCosintPort_getMask(DiCosintPort *_this)               { return bdaq_obj_get(61, uint8)(_this);         }
   __inline ErrorCode  DiCosintPort_setMask(DiCosintPort *_this, uint8 value)  { return bdaq_obj_set(62, uint8)(_this, value);  }

   // ----------------------------------------------------------
   // common classes : DiPmintPort (method index: 63~67)
   // ----------------------------------------------------------
   __inline int32       DiPmintPort_getPort(DiPmintPort *_this)                 { return bdaq_obj_get(63, int32)(_this);        }
   __inline uint8       DiPmintPort_getMask(DiPmintPort *_this)                 { return bdaq_obj_get(64, uint8)(_this);        }
   __inline ErrorCode   DiPmintPort_setMask(DiPmintPort *_this, uint8 value)    { return bdaq_obj_set(65, uint8)(_this, value); }
   __inline uint8       DiPmintPort_getPattern(DiPmintPort *_this)              { return bdaq_obj_get(66, uint8)(_this);        }
   __inline ErrorCode   DiPmintPort_setPattern(DiPmintPort *_this, uint8 value) { return bdaq_obj_set(67, uint8)(_this, value); }

   // ----------------------------------------------------------
   // common classes : ScanPort (method index: 68~75)
   // ----------------------------------------------------------
   __inline int32      ScanPort_getPortStart(ScanPort *_this)                  { return bdaq_obj_get(68, int32)(_this);        }
   __inline ErrorCode  ScanPort_setPortStart(ScanPort *_this, int32 value)     { return bdaq_obj_set(69, int32)(_this, value); }
   __inline int32      ScanPort_getPortCount(ScanPort *_this)                  { return bdaq_obj_get(70, int32)(_this);        }
   __inline ErrorCode  ScanPort_setPortCount(ScanPort *_this, int32 value)     { return bdaq_obj_set(71, int32)(_this, value); }
   __inline int32      ScanPort_getSamples(ScanPort *_this)                    { return bdaq_obj_get(72, int32)(_this);        }
   __inline ErrorCode  ScanPort_setSamples(ScanPort *_this, int32 value)       { return bdaq_obj_set(73, int32)(_this, value); }
   __inline int32      ScanPort_getIntervalCount(ScanPort *_this)              { return bdaq_obj_get(74, int32)(_this);        }
   __inline ErrorCode  ScanPort_setIntervalCount(ScanPort *_this, int32 value) { return bdaq_obj_set(75, int32)(_this, value); }

   // ----------------------------------------------------------
   // AI features (method index: 76~104)
   // ----------------------------------------------------------
   // ADC features
   __inline int32  AiFeatures_getResolution(AiFeatures *_this)                 { return bdaq_obj_get(76, int32)(_this); }
   __inline int32  AiFeatures_getDataSize(AiFeatures *_this)                   { return bdaq_obj_get(77, int32)(_this); }
   __inline int32  AiFeatures_getDataMask(AiFeatures *_this)                   { return bdaq_obj_get(78, int32)(_this); }
   // channel features                                                        
   __inline int32         AiFeatures_getChannelCountMax(AiFeatures *_this)     { return bdaq_obj_get(79, int32)(_this);        }
   __inline AiChannelType AiFeatures_getChannelType(AiFeatures *_this)         { return bdaq_obj_get(80, AiChannelType)(_this);}
   __inline int8          AiFeatures_getOverallValueRange(AiFeatures *_this)   { return bdaq_obj_get(81, int8)(_this);         }
   __inline int8          AiFeatures_getThermoSupported(AiFeatures *_this)     { return bdaq_obj_get(82, int8)(_this);         }
   __inline ICollection*  AiFeatures_getValueRanges(AiFeatures *_this)         { return bdaq_obj_get(83, ICollection*)(_this); }
   __inline ICollection*  AiFeatures_getBurnoutReturnTypes(AiFeatures *_this)  { return bdaq_obj_get(84, ICollection*)(_this); }
   // CJC features
   __inline ICollection*  AiFeatures_getCjcChannels(AiFeatures *_this)         { return bdaq_obj_get(85, ICollection*)(_this); }
   // buffered ai->basic features
   __inline int8           AiFeatures_getBufferedAiSupported(AiFeatures *_this){ return bdaq_obj_get(86, int8)(_this);           }
   __inline SamplingMethod AiFeatures_getSamplingMethod(AiFeatures *_this)     { return bdaq_obj_get(87, SamplingMethod)(_this); }
   __inline int32          AiFeatures_getChannelStartBase(AiFeatures *_this)   { return bdaq_obj_get(88, int32)(_this);          }
   __inline int32          AiFeatures_getChannelCountBase(AiFeatures *_this)   { return bdaq_obj_get(89, int32)(_this);          }
   // buffered ai->conversion clock features
   __inline ICollection*  AiFeatures_getConvertClockSources(AiFeatures *_this)                     { return bdaq_obj_get(90, ICollection*)(_this);           }
   __inline void          AiFeatures_getConvertClockRange(AiFeatures *_this, MathInterval *value)  { bdaq_obj_get_v1(91, void, MathInterval *)(_this, value);}
   // buffered ai->burst scan
   __inline int8          AiFeatures_getBurstScanSupported(AiFeatures *_this)                      { return bdaq_obj_get(92, int8)(_this);                    }
   __inline ICollection*  AiFeatures_getScanClockSources(AiFeatures *_this)                        { return bdaq_obj_get(93, ICollection*)(_this);            }
   __inline void          AiFeatures_getScanClockRange(AiFeatures *_this, MathInterval *value)     { bdaq_obj_get_v1(94, void, MathInterval *)(_this, value); }
   __inline int32         AiFeatures_getScanCountMax(AiFeatures *_this)                            { return bdaq_obj_get(95, int32)(_this);                   }
   // buffered ai->trigger features
   __inline int8          AiFeatures_getTriggerSupported(AiFeatures *_this)                        { return bdaq_obj_get(96, int8)(_this);                    }
   __inline int32         AiFeatures_getTriggerCount(AiFeatures *_this)                            { return bdaq_obj_get(97, int32)(_this);                   }
   __inline ICollection*  AiFeatures_getTriggerSources(AiFeatures *_this)                          { return bdaq_obj_get(98, ICollection*)(_this);            }
   __inline ICollection*  AiFeatures_getTriggerActions(AiFeatures *_this)                          { return bdaq_obj_get(99, ICollection*)(_this);            }
   __inline void          AiFeatures_getTriggerDelayRange(AiFeatures *_this, MathInterval *value)  { bdaq_obj_get_v1(100, void, MathInterval *)(_this, value);}
   // buffered ai->trigger1 features
   __inline int8          AiFeatures_getTrigger1Supported(AiFeatures *_this)                       { return bdaq_obj_get(101, int8)(_this);                   }
   __inline ICollection*  AiFeatures_getTrigger1Sources(AiFeatures *_this)                         { return bdaq_obj_get(102, ICollection*)(_this);           }
   __inline ICollection*  AiFeatures_getTrigger1Actions(AiFeatures *_this)                         { return bdaq_obj_get(103, ICollection*)(_this);           }
   __inline void          AiFeatures_getTrigger1DelayRange(AiFeatures *_this, MathInterval *value) { bdaq_obj_get_v1(104, void, MathInterval *)(_this, value);}

   // ----------------------------------------------------------
   // InstantAiCtrl (method index: 105~126)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       InstantAiCtrl_Dispose(InstantAiCtrl *_this)                                                       { bdaq_obj_func(105, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       InstantAiCtrl_Cleanup(InstantAiCtrl *_this)                                                       { bdaq_obj_func(106, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  InstantAiCtrl_UpdateProperties(InstantAiCtrl *_this)                                              { return bdaq_obj_func(107, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       InstantAiCtrl_addRemovedListener(InstantAiCtrl *_this, DeviceEventListener * listener)            { bdaq_obj_func(108, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAiCtrl_removeRemovedListener(InstantAiCtrl *_this, DeviceEventListener * listener)         { bdaq_obj_func(109, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAiCtrl_addReconnectedListener(InstantAiCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(110, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAiCtrl_removeReconnectedListener(InstantAiCtrl *_this, DeviceEventListener * listener)     { bdaq_obj_func(111, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAiCtrl_addPropertyChangedListener(InstantAiCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(112, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAiCtrl_removePropertyChangedListener(InstantAiCtrl *_this, DeviceEventListener * listener) { bdaq_obj_func(113, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAiCtrl_getSelectedDevice(InstantAiCtrl *_this, DeviceInformation *x)                       { bdaq_obj_get_v1(114, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  InstantAiCtrl_setSelectedDevice(InstantAiCtrl *_this, DeviceInformation const *x)                 { return bdaq_obj_set(115, DeviceInformation const *)(_this, x);            }
   __inline int8       InstantAiCtrl_getInitialized(InstantAiCtrl *_this)                                                { return bdaq_obj_get(116, int8)(_this);                                    }
   __inline int8       InstantAiCtrl_getCanEditProperty(InstantAiCtrl *_this)                                            { return bdaq_obj_get(117, int8)(_this);                                    }
   __inline HANDLE     InstantAiCtrl_getDevice(InstantAiCtrl *_this)                                                     { return bdaq_obj_get(118, HANDLE)(_this);                                  }
   __inline HANDLE     InstantAiCtrl_getModule(InstantAiCtrl *_this)                                                     { return bdaq_obj_get(119, HANDLE)(_this);                                  }
   __inline ICollection* InstantAiCtrl_getSupportedDevices(InstantAiCtrl *_this)                                         { return bdaq_obj_get(120, ICollection*)(_this);                            }
   __inline ICollection* InstantAiCtrl_getSupportedModes(InstantAiCtrl *_this)                                           { return bdaq_obj_get(121, ICollection*)(_this);                            }
   /* Methods derived from AiCtrlBase */
   __inline AiFeatures*  InstantAiCtrl_getFeatures(InstantAiCtrl *_this)                                                 { return bdaq_obj_get(122, AiFeatures* )(_this);                            }
   __inline ICollection* InstantAiCtrl_getChannels(InstantAiCtrl *_this)                                                 { return bdaq_obj_get(123, ICollection*)(_this);                            }
   __inline int32        InstantAiCtrl_getChannelCount(InstantAiCtrl *_this)                                             { return bdaq_obj_get(124, int32)(_this);                                   }
   /* InstantAiCtrl methods */
   __inline ErrorCode    InstantAiCtrl_ReadAny(InstantAiCtrl *_this, int32 chStart, int32 chCount, void *dataRaw, double *dataScaled) { return bdaq_obj_func(125, (ErrorCode (BDAQCALL *)(void *, int32, int32, void *, double *)))(_this, chStart, chCount, dataRaw, dataScaled); }
   __inline CjcSetting*  InstantAiCtrl_getCjc(InstantAiCtrl *_this)                                                                   { return bdaq_obj_get(126, CjcSetting*)(_this);                }

   // ----------------------------------------------------------
   // BufferedAiCtrl (method index: 127~173)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       BufferedAiCtrl_Dispose(BufferedAiCtrl *_this)                                                      { bdaq_obj_func(127, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       BufferedAiCtrl_Cleanup(BufferedAiCtrl *_this)                                                      { bdaq_obj_func(128, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  BufferedAiCtrl_UpdateProperties(BufferedAiCtrl *_this)                                             { return bdaq_obj_func(129, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       BufferedAiCtrl_addRemovedListener(BufferedAiCtrl *_this, DeviceEventListener * listener)           { bdaq_obj_func(130, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_removeRemovedListener(BufferedAiCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(131, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_addReconnectedListener(BufferedAiCtrl *_this, DeviceEventListener * listener)       { bdaq_obj_func(132, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_removeReconnectedListener(BufferedAiCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(133, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_addPropertyChangedListener(BufferedAiCtrl *_this, DeviceEventListener * listener)   { bdaq_obj_func(134, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_removePropertyChangedListener(BufferedAiCtrl *_this, DeviceEventListener * listener){ bdaq_obj_func(135, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_getSelectedDevice(BufferedAiCtrl *_this, DeviceInformation *x)                      { bdaq_obj_get_v1(136, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  BufferedAiCtrl_setSelectedDevice(BufferedAiCtrl *_this, DeviceInformation const *x)                { return bdaq_obj_set(137, DeviceInformation const *)(_this, x);            }
   __inline int8       BufferedAiCtrl_getInitialized(BufferedAiCtrl *_this)                                               { return bdaq_obj_get(138, int8)(_this);                                    }
   __inline int8       BufferedAiCtrl_getCanEditProperty(BufferedAiCtrl *_this)                                           { return bdaq_obj_get(139, int8)(_this);                                    }
   __inline HANDLE     BufferedAiCtrl_getDevice(BufferedAiCtrl *_this)                                                    { return bdaq_obj_get(140, HANDLE)(_this);                                  }
   __inline HANDLE     BufferedAiCtrl_getModule(BufferedAiCtrl *_this)                                                    { return bdaq_obj_get(141, HANDLE)(_this);                                  }
   __inline ICollection*  BufferedAiCtrl_getSupportedDevices(BufferedAiCtrl *_this)                                       { return bdaq_obj_get(142, ICollection*)(_this);                            }
   __inline ICollection*  BufferedAiCtrl_getSupportedModes(BufferedAiCtrl *_this)                                         { return bdaq_obj_get(143, ICollection*)(_this);                            }
   /* Methods derived from AiCtrlBase */                                                                                  
   __inline AiFeatures*   BufferedAiCtrl_getFeatures(BufferedAiCtrl *_this)                                               { return bdaq_obj_get(144, AiFeatures* )(_this);                            }
   __inline ICollection*  BufferedAiCtrl_getChannels(BufferedAiCtrl *_this)                                               { return bdaq_obj_get(145, ICollection*)(_this);                            }
   __inline int32         BufferedAiCtrl_getChannelCount(BufferedAiCtrl *_this)                                           { return bdaq_obj_get(146, int32)(_this);                                   }
   /* BufferedAiCtrl methods */
   // event
   __inline void       BufferedAiCtrl_addDataReadyListener(BufferedAiCtrl *_this, BfdAiEventListener *listener)           { bdaq_obj_func(147, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_removeDataReadyListener(BufferedAiCtrl *_this, BfdAiEventListener *listener)        { bdaq_obj_func(148, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_addOverrunListener(BufferedAiCtrl *_this, BfdAiEventListener *listener)             { bdaq_obj_func(149, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_removeOverrunListener(BufferedAiCtrl *_this, BfdAiEventListener *listener)          { bdaq_obj_func(150, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_addCacheOverflowListener(BufferedAiCtrl *_this, BfdAiEventListener *listener)       { bdaq_obj_func(151, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_removeCacheOverflowListener(BufferedAiCtrl *_this, BfdAiEventListener *listener)    { bdaq_obj_func(152, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_addStoppedListener(BufferedAiCtrl *_this, BfdAiEventListener *listener)             { bdaq_obj_func(153, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_removeStoppedListener(BufferedAiCtrl *_this, BfdAiEventListener *listener)          { bdaq_obj_func(154, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   // method
   __inline ErrorCode  BufferedAiCtrl_Prepare(BufferedAiCtrl *_this)                                                      { return bdaq_obj_func(155, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode  BufferedAiCtrl_RunOnce(BufferedAiCtrl *_this)                                                      { return bdaq_obj_func(156, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode  BufferedAiCtrl_Start(BufferedAiCtrl *_this)                                                        { return bdaq_obj_func(157, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode  BufferedAiCtrl_Stop(BufferedAiCtrl *_this)                                                         { return bdaq_obj_func(158, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode  BufferedAiCtrl_GetDataI16(BufferedAiCtrl *_this, int32 count, int16 rawData[])                     { return bdaq_obj_func(159, (ErrorCode (BDAQCALL *)(void *, int32, int16*)))(_this, count, rawData);    }
   __inline ErrorCode  BufferedAiCtrl_GetDataI32(BufferedAiCtrl *_this, int32 count, int32 rawData[])                     { return bdaq_obj_func(160, (ErrorCode (BDAQCALL *)(void *, int32, int32*)))(_this, count, rawData);    }
   __inline ErrorCode  BufferedAiCtrl_GetDataF64(BufferedAiCtrl *_this, int32 count, double scaledData[])                 { return bdaq_obj_func(161, (ErrorCode (BDAQCALL *)(void *, int32, double*)))(_this, count, scaledData);}
   __inline void       BufferedAiCtrl_Release(BufferedAiCtrl *_this)                                                      {        bdaq_obj_func(162, (void (BDAQCALL *)(void *)))(_this);            }
   // property
   __inline void*         BufferedAiCtrl_getBuffer(BufferedAiCtrl *_this)                                                 { return bdaq_obj_get(163, void*)(_this);         }
   __inline int32         BufferedAiCtrl_getBufferCapacity(BufferedAiCtrl *_this)                                         { return bdaq_obj_get(164, int32)(_this);         }
   __inline ControlState  BufferedAiCtrl_getState(BufferedAiCtrl *_this)                                                  { return bdaq_obj_get(165, ControlState)(_this);  }
   __inline ScanChannel*  BufferedAiCtrl_getScanChannel(BufferedAiCtrl *_this)                                            { return bdaq_obj_get(166, ScanChannel*)(_this);  }
   __inline ConvertClock* BufferedAiCtrl_getConvertClock(BufferedAiCtrl *_this)                                           { return bdaq_obj_get(167, ConvertClock*)(_this); }
   __inline ScanClock*    BufferedAiCtrl_getScanClock(BufferedAiCtrl *_this)                                              { return bdaq_obj_get(168, ScanClock*)(_this);    }
   __inline Trigger*      BufferedAiCtrl_getTrigger(BufferedAiCtrl *_this)                                                { return bdaq_obj_get(169, Trigger*)(_this);      }
   __inline int8          BufferedAiCtrl_getStreaming(BufferedAiCtrl *_this)                                              { return bdaq_obj_get(170, int8)(_this);          }
   __inline ErrorCode     BufferedAiCtrl_setStreaming(BufferedAiCtrl *_this, int8 value)                                  { return bdaq_obj_set(171, int8)(_this, value);   }
   // method
   __inline ErrorCode     BufferedAiCtrl_GetEventStatus(BufferedAiCtrl *_this, EventId id, int32 *status)                 { return bdaq_obj_func(172, (ErrorCode (BDAQCALL *)(void *, EventId, int32*)))(_this, id, status); }
   // property
   __inline Trigger*      BufferedAiCtrl_getTrigger1(BufferedAiCtrl *_this)                                               { return bdaq_obj_get(173, Trigger*)(_this);      }   

   // ----------------------------------------------------------
   // AO features (method index: 174~195)
   // ----------------------------------------------------------
   // DAC features                                                               
   __inline int32  AoFeatures_getResolution(AoFeatures *_this)                                     { return bdaq_obj_get(174, int32)(_this);                   }
   __inline int32  AoFeatures_getDataSize(AoFeatures *_this)                                       { return bdaq_obj_get(175, int32)(_this);                   }
   __inline int32  AoFeatures_getDataMask(AoFeatures *_this)                                       { return bdaq_obj_get(176, int32)(_this);                   }
   // channel features                                                                               
   __inline int32        AoFeatures_getChannelCountMax(AoFeatures *_this)                          { return bdaq_obj_get(177, int32)(_this);                   }
   __inline ICollection* AoFeatures_getValueRanges(AoFeatures *_this)                              { return bdaq_obj_get(178, ICollection*)(_this);            }
   __inline int8         AoFeatures_getExternalRefAntiPolar(AoFeatures *_this)                     { return bdaq_obj_get(179, int8)(_this);                    }
   __inline void         AoFeatures_getExternalRefRange(AoFeatures *_this, MathInterval *value)    { bdaq_obj_get_v1(180, void, MathInterval *)(_this, value); }
   // buffered ao->basic features                                                
   __inline int8           AoFeatures_getBufferedAoSupported(AoFeatures *_this)                    { return bdaq_obj_get(181, int8)(_this);                    }
   __inline SamplingMethod AoFeatures_getSamplingMethod(AoFeatures *_this)                         { return bdaq_obj_get(182, SamplingMethod)(_this);          }
   __inline int32          AoFeatures_getChannelStartBase(AoFeatures *_this)                       { return bdaq_obj_get(183, int32)(_this);                   }
   __inline int32          AoFeatures_getChannelCountBase(AoFeatures *_this)                       { return bdaq_obj_get(184, int32)(_this);                   }
   // buffered ao->conversion clock features                                                       
   __inline ICollection*   AoFeatures_getConvertClockSources(AoFeatures *_this)                    { return bdaq_obj_get(185, ICollection*)(_this);            }
   __inline void           AoFeatures_getConvertClockRange(AoFeatures *_this, MathInterval *value) { bdaq_obj_get_v1(186, void, MathInterval *)(_this, value); }
   // buffered ao->trigger features                                              
   __inline int8           AoFeatures_getTriggerSupported(AoFeatures *_this)                       { return bdaq_obj_get(187, int8)(_this);                    }
   __inline int32          AoFeatures_getTriggerCount(AoFeatures *_this)                           { return bdaq_obj_get(188, int32)(_this);                   }
   __inline ICollection*   AoFeatures_getTriggerSources(AoFeatures *_this)                         { return bdaq_obj_get(189, ICollection*)(_this);            }
   __inline ICollection*   AoFeatures_getTriggerActions(AoFeatures *_this)                         { return bdaq_obj_get(190, ICollection*)(_this);            }
   __inline void           AoFeatures_getTriggerDelayRange(AoFeatures *_this, MathInterval *value) { bdaq_obj_get_v1(191, void, MathInterval *)(_this, value); }
   // buffered ao->trigger1 features                                                               
   __inline int8           AoFeatures_getTrigger1Supported(AoFeatures *_this)                      { return bdaq_obj_get(192, int8)(_this);                    }
   __inline ICollection*   AoFeatures_getTrigger1Sources(AoFeatures *_this)                        { return bdaq_obj_get(193, ICollection*)(_this);            }
   __inline ICollection*   AoFeatures_getTrigger1Actions(AoFeatures *_this)                        { return bdaq_obj_get(194, ICollection*)(_this);            }
   __inline void           AoFeatures_getTrigger1DelayRange(AoFeatures *_this, MathInterval *value){ bdaq_obj_get_v1(195, void, MathInterval *)(_this, value); }

   // ----------------------------------------------------------
   // InstantAoCtrl (method index: 196~220)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       InstantAoCtrl_Dispose(InstantAoCtrl *_this)                                                       { bdaq_obj_func(196, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       InstantAoCtrl_Cleanup(InstantAoCtrl *_this)                                                       { bdaq_obj_func(197, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  InstantAoCtrl_UpdateProperties(InstantAoCtrl *_this)                                              { return bdaq_obj_func(198, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       InstantAoCtrl_addRemovedListener(InstantAoCtrl *_this, DeviceEventListener * listener)            { bdaq_obj_func(199, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAoCtrl_removeRemovedListener(InstantAoCtrl *_this, DeviceEventListener * listener)         { bdaq_obj_func(200, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAoCtrl_addReconnectedListener(InstantAoCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(201, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAoCtrl_removeReconnectedListener(InstantAoCtrl *_this, DeviceEventListener * listener)     { bdaq_obj_func(202, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAoCtrl_addPropertyChangedListener(InstantAoCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(203, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAoCtrl_removePropertyChangedListener(InstantAoCtrl *_this, DeviceEventListener * listener) { bdaq_obj_func(204, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantAoCtrl_getSelectedDevice(InstantAoCtrl *_this, DeviceInformation *x)                       { bdaq_obj_get_v1(205, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  InstantAoCtrl_setSelectedDevice(InstantAoCtrl *_this, DeviceInformation const *x)                 { return bdaq_obj_set(206, DeviceInformation const *)(_this, x);            }
   __inline int8       InstantAoCtrl_getInitialized(InstantAoCtrl *_this)                                                { return bdaq_obj_get(207, int8)(_this);                                    }
   __inline int8       InstantAoCtrl_getCanEditProperty(InstantAoCtrl *_this)                                            { return bdaq_obj_get(208, int8)(_this);                                    }
   __inline HANDLE     InstantAoCtrl_getDevice(InstantAoCtrl *_this)                                                     { return bdaq_obj_get(209, HANDLE)(_this);                                  }
   __inline HANDLE     InstantAoCtrl_getModule(InstantAoCtrl *_this)                                                     { return bdaq_obj_get(210, HANDLE)(_this);                                  }
   __inline ICollection* InstantAoCtrl_getSupportedDevices(InstantAoCtrl *_this)                                         { return bdaq_obj_get(211, ICollection*)(_this);                            }
   __inline ICollection* InstantAoCtrl_getSupportedModes(InstantAoCtrl *_this)                                           { return bdaq_obj_get(212, ICollection*)(_this);                            }
   /* Methods derived from AiCtrlBase */                                                                                 
   __inline AoFeatures*  InstantAoCtrl_getFeatures(InstantAoCtrl *_this)                                                 { return bdaq_obj_get(213, AoFeatures*)(_this);                             }
   __inline ICollection* InstantAoCtrl_getChannels(InstantAoCtrl *_this)                                                 { return bdaq_obj_get(214, ICollection*)(_this);                            }
   __inline int32        InstantAoCtrl_getChannelCount(InstantAoCtrl *_this)                                             { return bdaq_obj_get(215, int32)(_this);                                   }
   __inline double       InstantAoCtrl_getExtRefValueForUnipolar(InstantAoCtrl *_this)                                   { return bdaq_obj_get(216, double)(_this);                                  }
   __inline ErrorCode    InstantAoCtrl_setExtRefValueForUnipolar(InstantAoCtrl *_this, double value)                     { return bdaq_obj_set(217, double)(_this, value);                           }
   __inline double       InstantAoCtrl_getExtRefValueForBipolar(InstantAoCtrl *_this)                                    { return bdaq_obj_get(218, double)(_this);                                  }
   __inline ErrorCode    InstantAoCtrl_setExtRefValueForBipolar(InstantAoCtrl *_this, double value)                      { return bdaq_obj_set(219, double)(_this, value);                           }
   /* InstantAoCtrl methods */
   __inline ErrorCode    InstantAoCtrl_WriteAny(InstantAoCtrl *_this, int32 chStart, int32 chCount, void *dataRaw, double *dataScaled) { return bdaq_obj_func(220, (ErrorCode (BDAQCALL *)(void *, int32, int32, void *, double *)))(_this, chStart, chCount, dataRaw, dataScaled); }

   // ----------------------------------------------------------
   // BufferedAoCtrl (method index: 221~271)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       BufferedAoCtrl_Dispose(BufferedAoCtrl *_this)                                                      { bdaq_obj_func(221, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       BufferedAoCtrl_Cleanup(BufferedAoCtrl *_this)                                                      { bdaq_obj_func(222, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  BufferedAoCtrl_UpdateProperties(BufferedAoCtrl *_this)                                             { return bdaq_obj_func(223, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       BufferedAoCtrl_addRemovedListener(BufferedAoCtrl *_this, DeviceEventListener * listener)           { bdaq_obj_func(224, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_removeRemovedListener(BufferedAoCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(225, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_addReconnectedListener(BufferedAoCtrl *_this, DeviceEventListener * listener)       { bdaq_obj_func(226, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_removeReconnectedListener(BufferedAoCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(227, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_addPropertyChangedListener(BufferedAoCtrl *_this, DeviceEventListener * listener)   { bdaq_obj_func(228, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_removePropertyChangedListener(BufferedAoCtrl *_this, DeviceEventListener * listener){ bdaq_obj_func(229, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_getSelectedDevice(BufferedAoCtrl *_this, DeviceInformation *x)                      { bdaq_obj_get_v1(230, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  BufferedAoCtrl_setSelectedDevice(BufferedAoCtrl *_this, DeviceInformation const *x)                { return bdaq_obj_set(231, DeviceInformation const *)(_this, x);            }
   __inline int8       BufferedAoCtrl_getInitialized(BufferedAoCtrl *_this)                                               { return bdaq_obj_get(232, int8)(_this);                                    }
   __inline int8       BufferedAoCtrl_getCanEditProperty(BufferedAoCtrl *_this)                                           { return bdaq_obj_get(233, int8)(_this);                                    }
   __inline HANDLE     BufferedAoCtrl_getDevice(BufferedAoCtrl *_this)                                                    { return bdaq_obj_get(234, HANDLE)(_this);                                  }
   __inline HANDLE     BufferedAoCtrl_getModule(BufferedAoCtrl *_this)                                                    { return bdaq_obj_get(235, HANDLE)(_this);                                  }
   __inline ICollection*  BufferedAoCtrl_getSupportedDevices(BufferedAoCtrl *_this)                                       { return bdaq_obj_get(236, ICollection*)(_this);                            }
   __inline ICollection*  BufferedAoCtrl_getSupportedModes(BufferedAoCtrl *_this)                                         { return bdaq_obj_get(237, ICollection*)(_this);                            }
   /* Methods derived from AiCtrlBase */                                                                                  
   __inline AoFeatures*   BufferedAoCtrl_getFeatures(BufferedAoCtrl *_this)                                               { return bdaq_obj_get(238, AoFeatures*)(_this);                             }
   __inline ICollection*  BufferedAoCtrl_getChannels(BufferedAoCtrl *_this)                                               { return bdaq_obj_get(239, ICollection*)(_this);                            }
   __inline int32         BufferedAoCtrl_getChannelCount(BufferedAoCtrl *_this)                                           { return bdaq_obj_get(240, int32)(_this);                                   }
   __inline double        BufferedAoCtrl_getExtRefValueForUnipolar(InstantAoCtrl *_this)                                  { return bdaq_obj_get(241, double)(_this);                                  }
   __inline ErrorCode     BufferedAoCtrl_setExtRefValueForUnipolar(InstantAoCtrl *_this, double value)                    { return bdaq_obj_set(242, double)(_this, value);                           }
   __inline double        BufferedAoCtrl_getExtRefValueForBipolar(InstantAoCtrl *_this)                                   { return bdaq_obj_get(243, double)(_this);                                  }
   __inline ErrorCode     BufferedAoCtrl_setExtRefValueForBipolar(InstantAoCtrl *_this, double value)                     { return bdaq_obj_set(244, double)(_this, value);                           }
   /* BufferedAoCtrl methods */
   // event
   __inline void       BufferedAoCtrl_addDataTransmittedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener)     { bdaq_obj_func(245, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_removeDataTransmittedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener)  { bdaq_obj_func(246, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_addUnderrunListener(BufferedAoCtrl *_this, BfdAoEventListener *listener)            { bdaq_obj_func(247, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_removeUnderrunListener(BufferedAoCtrl *_this, BfdAoEventListener *listener)         { bdaq_obj_func(248, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_addCacheEmptiedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener)        { bdaq_obj_func(249, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_removeCacheEmptiedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener)     { bdaq_obj_func(250, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_addTransitStoppedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener)      { bdaq_obj_func(251, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_removeTransitStoppedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener)   { bdaq_obj_func(252, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_addStoppedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener)             { bdaq_obj_func(253, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAoCtrl_removeStoppedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener)          { bdaq_obj_func(254, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   // method
   __inline ErrorCode  BufferedAoCtrl_Prepare(BufferedAoCtrl *_this)                                                      { return bdaq_obj_func(255, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode  BufferedAoCtrl_RunOnce(BufferedAoCtrl *_this)                                                      { return bdaq_obj_func(256, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode  BufferedAoCtrl_Start(BufferedAoCtrl *_this)                                                        { return bdaq_obj_func(257, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode  BufferedAoCtrl_Stop(BufferedAoCtrl *_this, int32 action)                                           { return bdaq_obj_func(258, (ErrorCode (BDAQCALL *)(void *, int32)))(_this,action);                     }
   __inline ErrorCode  BufferedAoCtrl_SetDataI16(BufferedAoCtrl *_this, int32 count, int16 rawData[])                     { return bdaq_obj_func(259, (ErrorCode (BDAQCALL *)(void *, int32, int16*)))(_this, count, rawData);    }
   __inline ErrorCode  BufferedAoCtrl_SetDataI32(BufferedAoCtrl *_this, int32 count, int32 rawData[])                     { return bdaq_obj_func(260, (ErrorCode (BDAQCALL *)(void *, int32, int32*)))(_this, count, rawData);    }
   __inline ErrorCode  BufferedAoCtrl_SetDataF64(BufferedAoCtrl *_this, int32 count, double scaledData[])                 { return bdaq_obj_func(261, (ErrorCode (BDAQCALL *)(void *, int32, double*)))(_this, count, scaledData);}
   __inline void       BufferedAoCtrl_Release(BufferedAoCtrl *_this)                                                      {        bdaq_obj_func(262, (void (BDAQCALL *)(void *)))(_this);            }
   // property
   __inline void*         BufferedAoCtrl_getBuffer(BufferedAoCtrl *_this)                                                 { return bdaq_obj_get(263, void*)(_this);         }
   __inline int32         BufferedAoCtrl_getBufferCapacity(BufferedAoCtrl *_this)                                         { return bdaq_obj_get(264, int32)(_this);         }
   __inline ControlState  BufferedAoCtrl_getState(BufferedAoCtrl *_this)                                                  { return bdaq_obj_get(265, ControlState)(_this);  }
   __inline ScanChannel*  BufferedAoCtrl_getScanChannel(BufferedAoCtrl *_this)                                            { return bdaq_obj_get(266, ScanChannel*)(_this);  }
   __inline ConvertClock* BufferedAoCtrl_getConvertClock(BufferedAoCtrl *_this)                                           { return bdaq_obj_get(267, ConvertClock*)(_this); }
   __inline Trigger*      BufferedAoCtrl_getTrigger(BufferedAoCtrl *_this)                                                { return bdaq_obj_get(268, Trigger*)(_this);      }
   __inline int8          BufferedAoCtrl_getStreaming(BufferedAoCtrl *_this)                                              { return bdaq_obj_get(269, int8)(_this);          }
   __inline ErrorCode     BufferedAoCtrl_setStreaming(BufferedAoCtrl *_this, int8 value)                                  { return bdaq_obj_set(270, int8)(_this, value);   }
   __inline Trigger*      BufferedAoCtrl_getTrigger1(BufferedAoCtrl *_this)                                               { return bdaq_obj_get(271, Trigger*)(_this);      }

   // ----------------------------------------------------------
   // DI features (method index: 272~304)
   // ----------------------------------------------------------
   __inline int8          DiFeatures_getPortProgrammable(DiFeatures *_this)                                { return bdaq_obj_get(272, int8 )(_this);                   }
   __inline int32         DiFeatures_getPortCount(DiFeatures *_this)                                       { return bdaq_obj_get(273, int32)(_this);                   }
   __inline ICollection*  DiFeatures_getPortsType(DiFeatures *_this)                                       { return bdaq_obj_get(274, ICollection*)(_this);            }
   __inline int8          DiFeatures_getDiSupported(DiFeatures *_this)                                     { return bdaq_obj_get(275, int8 )(_this);                   }
   __inline int8          DiFeatures_getDoSupported(DiFeatures *_this)                                     { return bdaq_obj_get(276, int8 )(_this);                   }
   __inline int32         DiFeatures_getChannelCountMax(DiFeatures *_this)                                 { return bdaq_obj_get(277, int32)(_this);                   }
   __inline ICollection*  DiFeatures_getDataMask(DiFeatures *_this)                                        { return bdaq_obj_get(278, ICollection*)(_this);            }
   // di noise filter features                                                                                      
   __inline int8          DiFeatures_getNoiseFilterSupported(DiFeatures *_this)                            { return bdaq_obj_get(279, int8)(_this);                    }
   __inline ICollection*  DiFeatures_getNoiseFilterOfChannels(DiFeatures *_this)                           { return bdaq_obj_get(280, ICollection*)(_this);            }
   __inline void          DiFeatures_getNoiseFilterBlockTimeRange(DiFeatures *_this, MathInterval *value)  { bdaq_obj_get_v1(281, void, MathInterval *)(_this, value); }
   // di interrupt features                                                               
   __inline int8          DiFeatures_getDiintSupported(DiFeatures *_this)                                  { return bdaq_obj_get(282, int8)(_this);                    }
   __inline int8          DiFeatures_getDiintGateSupported(DiFeatures *_this)                              { return bdaq_obj_get(283, int8)(_this);                    }
   __inline int8          DiFeatures_getDiCosintSupported(DiFeatures *_this)                               { return bdaq_obj_get(284, int8)(_this);                    }
   __inline int8          DiFeatures_getDiPmintSupported(DiFeatures *_this)                                { return bdaq_obj_get(285, int8)(_this);                    }
   __inline ICollection*  DiFeatures_getDiintTriggerEdges(DiFeatures *_this)                               { return bdaq_obj_get(286, ICollection*)(_this);            }
   __inline ICollection*  DiFeatures_getDiintOfChannels(DiFeatures *_this)                                 { return bdaq_obj_get(287, ICollection*)(_this);            }
   __inline ICollection*  DiFeatures_getDiintGateOfChannels(DiFeatures *_this)                             { return bdaq_obj_get(288, ICollection*)(_this);            }
   __inline ICollection*  DiFeatures_getDiCosintOfPorts(DiFeatures *_this)                                 { return bdaq_obj_get(289, ICollection*)(_this);            }
   __inline ICollection*  DiFeatures_getDiPmintOfPorts(DiFeatures *_this)                                  { return bdaq_obj_get(290, ICollection*)(_this);            }
   __inline ICollection*  DiFeatures_getSnapEventSources(DiFeatures *_this)                                { return bdaq_obj_get(291, ICollection*)(_this);            }
   // buffered di->basic features                                                         
   __inline int8           DiFeatures_getBufferedDiSupported(DiFeatures *_this)                            { return bdaq_obj_get(292, int8)(_this);                    }
   __inline SamplingMethod DiFeatures_getSamplingMethod(DiFeatures *_this)                                 { return bdaq_obj_get(293, SamplingMethod)(_this);          }
   // buffered di->conversion clock features                                              
   __inline ICollection*  DiFeatures_getConvertClockSources(DiFeatures *_this)                             { return bdaq_obj_get(294, ICollection*)(_this);            }
   __inline void          DiFeatures_getConvertClockRange(DiFeatures *_this, MathInterval *value)          { bdaq_obj_get_v1(295, void, MathInterval *)(_this, value); }
   // buffered di->burst scan                                                             
   __inline int8          DiFeatures_getBurstScanSupported(DiFeatures *_this)                              { return bdaq_obj_get(296, int8)(_this);                    }
   __inline ICollection*  DiFeatures_getScanClockSources(DiFeatures *_this)                                { return bdaq_obj_get(297, ICollection*)(_this);            }
   __inline void          DiFeatures_getScanClockRange(DiFeatures *_this, MathInterval *value)             { bdaq_obj_get_v1(298, void, MathInterval *)(_this, value); }
   __inline int32         DiFeatures_getScanCountMax(DiFeatures *_this)                                    { return bdaq_obj_get(299, int32)(_this);                   }
   // buffered di->trigger features                                                       
   __inline int8          DiFeatures_getTriggerSupported(DiFeatures *_this)                                { return bdaq_obj_get(300, int8 )(_this);                   }
   __inline int32         DiFeatures_getTriggerCount(DiFeatures *_this)                                    { return bdaq_obj_get(301, int32)(_this);                   }
   __inline ICollection*  DiFeatures_getTriggerSources(DiFeatures *_this)                                  { return bdaq_obj_get(302, ICollection*)(_this);            }
   __inline ICollection*  DiFeatures_getTriggerActions(DiFeatures *_this)                                  { return bdaq_obj_get(303, ICollection*)(_this);            }
   __inline void          DiFeatures_getTriggerDelayRange(DiFeatures *_this, MathInterval *value)          { bdaq_obj_get_v1(304, void, MathInterval *)(_this, value); }

   // ----------------------------------------------------------
   // InstantDiCtrl (method index: 305~337)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       InstantDiCtrl_Dispose(InstantDiCtrl *_this)                                                      { bdaq_obj_func(305, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       InstantDiCtrl_Cleanup(InstantDiCtrl *_this)                                                      { bdaq_obj_func(306, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  InstantDiCtrl_UpdateProperties(InstantDiCtrl *_this)                                             { return bdaq_obj_func(307, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       InstantDiCtrl_addRemovedListener(InstantDiCtrl *_this, DeviceEventListener * listener)           { bdaq_obj_func(308, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDiCtrl_removeRemovedListener(InstantDiCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(309, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDiCtrl_addReconnectedListener(InstantDiCtrl *_this, DeviceEventListener * listener)       { bdaq_obj_func(310, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDiCtrl_removeReconnectedListener(InstantDiCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(311, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDiCtrl_addPropertyChangedListener(InstantDiCtrl *_this, DeviceEventListener * listener)   { bdaq_obj_func(312, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDiCtrl_removePropertyChangedListener(InstantDiCtrl *_this, DeviceEventListener * listener){ bdaq_obj_func(313, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDiCtrl_getSelectedDevice(InstantDiCtrl *_this, DeviceInformation *x)                      { bdaq_obj_get_v1(314, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  InstantDiCtrl_setSelectedDevice(InstantDiCtrl *_this, DeviceInformation const *x)                { return bdaq_obj_set(315, DeviceInformation const *)(_this, x);            }
   __inline int8       InstantDiCtrl_getInitialized(InstantDiCtrl *_this)                                               { return bdaq_obj_get(316, int8)(_this);                                    }
   __inline int8       InstantDiCtrl_getCanEditProperty(InstantDiCtrl *_this)                                           { return bdaq_obj_get(317, int8)(_this);                                    }
   __inline HANDLE     InstantDiCtrl_getDevice(InstantDiCtrl *_this)                                                    { return bdaq_obj_get(318, HANDLE)(_this);                                  }
   __inline HANDLE     InstantDiCtrl_getModule(InstantDiCtrl *_this)                                                    { return bdaq_obj_get(319, HANDLE)(_this);                                  }
   __inline ICollection* InstantDiCtrl_getSupportedDevices(InstantDiCtrl *_this)                                        { return bdaq_obj_get(320, ICollection*)(_this);                            }
   __inline ICollection* InstantDiCtrl_getSupportedModes(InstantDiCtrl *_this)                                          { return bdaq_obj_get(321, ICollection*)(_this);                            }
   /* Methods derived from DioCtrlBase */
   __inline int32        InstantDiCtrl_getPortCount(InstantDiCtrl *_this)                                               { return bdaq_obj_get(322, int32)(_this);                                   }
   __inline ICollection* InstantDiCtrl_getPortDirection(InstantDiCtrl *_this)                                           { return bdaq_obj_get(323, ICollection*)(_this);                            }
   /* Methods derived from DiCtrlBase */ 
   __inline DiFeatures*  InstantDiCtrl_getFeatures(InstantDiCtrl *_this)                                                { return bdaq_obj_get(324, DiFeatures*)(_this);                             }
   __inline ICollection* InstantDiCtrl_getNoiseFilter(InstantDiCtrl *_this)                                             { return bdaq_obj_get(325, ICollection*)(_this);                            }
   /* Instant DI methods */
   // event
   __inline void         InstantDiCtrl_addInterruptListener(InstantDiCtrl *_this, DiSnapEventListener * listener)       { bdaq_obj_func(326, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void         InstantDiCtrl_removeInterruptListener(InstantDiCtrl *_this, DiSnapEventListener * listener)    { bdaq_obj_func(327, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void         InstantDiCtrl_addChangeOfStateListener(InstantDiCtrl *_this, DiSnapEventListener * listener)   { bdaq_obj_func(328, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void         InstantDiCtrl_removeChangeOfStateListener(InstantDiCtrl *_this, DiSnapEventListener * listener){ bdaq_obj_func(329, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void         InstantDiCtrl_addPatternMatchListener(InstantDiCtrl *_this, DiSnapEventListener * listener)    { bdaq_obj_func(330, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void         InstantDiCtrl_removePatternMatchListener(InstantDiCtrl *_this, DiSnapEventListener * listener) { bdaq_obj_func(331, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   // method                                                                                                            
   __inline ErrorCode    InstantDiCtrl_ReadAny(InstantDiCtrl *_this, int32 portStart, int32 portCount, uint8 data[])    { return bdaq_obj_func(332, (ErrorCode (BDAQCALL *)(void *, int32, int32, uint8*)))(_this, portStart, portCount, data); }
   __inline ErrorCode    InstantDiCtrl_SnapStart(InstantDiCtrl *_this)                                                  { return bdaq_obj_func(333, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode    InstantDiCtrl_SnapStop(InstantDiCtrl *_this)                                                   { return bdaq_obj_func(334, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   // property                                                                                                          
   __inline ICollection* InstantDiCtrl_getDiintChannels(InstantDiCtrl *_this)                                           { return bdaq_obj_get(335, ICollection*)(_this);                            }
   __inline ICollection* InstantDiCtrl_getDiCosintPorts(InstantDiCtrl *_this)                                           { return bdaq_obj_get(336, ICollection*)(_this);                            }
   __inline ICollection* InstantDiCtrl_getDiPmintPorts(InstantDiCtrl *_this)                                            { return bdaq_obj_get(337, ICollection*)(_this);                            }

   // ----------------------------------------------------------
   // BufferedDiCtrl (method index: 338~381)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       BufferedDiCtrl_Dispose(BufferedDiCtrl *_this)                                                      { bdaq_obj_func(338, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       BufferedDiCtrl_Cleanup(BufferedDiCtrl *_this)                                                      { bdaq_obj_func(339, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  BufferedDiCtrl_UpdateProperties(BufferedDiCtrl *_this)                                             { return bdaq_obj_func(340, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       BufferedDiCtrl_addRemovedListener(BufferedDiCtrl *_this, DeviceEventListener * listener)           { bdaq_obj_func(341, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDiCtrl_removeRemovedListener(BufferedDiCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(342, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDiCtrl_addReconnectedListener(BufferedDiCtrl *_this, DeviceEventListener * listener)       { bdaq_obj_func(343, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDiCtrl_removeReconnectedListener(BufferedDiCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(344, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDiCtrl_addPropertyChangedListener(BufferedDiCtrl *_this, DeviceEventListener * listener)   { bdaq_obj_func(345, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDiCtrl_removePropertyChangedListener(BufferedDiCtrl *_this, DeviceEventListener * listener){ bdaq_obj_func(346, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDiCtrl_getSelectedDevice(BufferedDiCtrl *_this, DeviceInformation *x)                      { bdaq_obj_get_v1(347, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  BufferedDiCtrl_setSelectedDevice(BufferedDiCtrl *_this, DeviceInformation const *x)                { return bdaq_obj_set(348, DeviceInformation const *)(_this, x);            }
   __inline int8       BufferedDiCtrl_getInitialized(BufferedDiCtrl *_this)                                               { return bdaq_obj_get(349, int8)(_this);                                    }
   __inline int8       BufferedDiCtrl_getCanEditProperty(BufferedDiCtrl *_this)                                           { return bdaq_obj_get(350, int8)(_this);                                    }
   __inline HANDLE     BufferedDiCtrl_getDevice(BufferedDiCtrl *_this)                                                    { return bdaq_obj_get(351, HANDLE)(_this);                                  }
   __inline HANDLE     BufferedDiCtrl_getModule(BufferedDiCtrl *_this)                                                    { return bdaq_obj_get(352, HANDLE)(_this);                                  }
   __inline ICollection*  BufferedDiCtrl_getSupportedDevices(BufferedDiCtrl *_this)                                       { return bdaq_obj_get(353, ICollection*)(_this);                            }
   __inline ICollection*  BufferedDiCtrl_getSupportedModes(BufferedDiCtrl *_this)                                         { return bdaq_obj_get(354, ICollection*)(_this);                            }
   /* Methods derived from DioCtrlBase */                                                                                 
   __inline int32         BufferedDiCtrl_getPortCount(BufferedDiCtrl *_this)                                              { return bdaq_obj_get(355, int32)(_this);                                   }
   __inline ICollection*  BufferedDiCtrl_getPortDirection(BufferedDiCtrl *_this)                                          { return bdaq_obj_get(356, ICollection*)(_this);                            }
   /* Methods derived from DiCtrlBase */                                                                                  
   __inline DiFeatures*   BufferedDiCtrl_getFeatures(BufferedDiCtrl *_this)                                               { return bdaq_obj_get(357, DiFeatures*)(_this);                             }
   __inline ICollection*  BufferedDiCtrl_getNoiseFilter(BufferedDiCtrl *_this)                                            { return bdaq_obj_get(358, ICollection*)(_this);                            }
   /* Buffered DI methods */
   // event
   __inline void          BufferedDiCtrl_addDataReadyListener(BufferedDiCtrl *_this, BfdDiEventListener *listener)        { bdaq_obj_func(359, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDiCtrl_removeDataReadyListener(BufferedDiCtrl *_this, BfdDiEventListener *listener)     { bdaq_obj_func(360, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDiCtrl_addOverrunListener(BufferedDiCtrl *_this, BfdDiEventListener *listener)          { bdaq_obj_func(361, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDiCtrl_removeOverrunListener(BufferedDiCtrl *_this, BfdDiEventListener *listener)       { bdaq_obj_func(362, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDiCtrl_addCacheOverflowListener(BufferedDiCtrl *_this, BfdDiEventListener *listener)    { bdaq_obj_func(363, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDiCtrl_removeCacheOverflowListener(BufferedDiCtrl *_this, BfdDiEventListener *listener) { bdaq_obj_func(364, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDiCtrl_addStoppedListener(BufferedDiCtrl *_this, BfdDiEventListener *listener)          { bdaq_obj_func(365, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDiCtrl_removeStoppedListener(BufferedDiCtrl *_this, BfdDiEventListener *listener)       { bdaq_obj_func(366, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   // method
   __inline ErrorCode     BufferedDiCtrl_Prepare(BufferedDiCtrl *_this)                                                   { return bdaq_obj_func(367, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode     BufferedDiCtrl_RunOnce(BufferedDiCtrl *_this)                                                   { return bdaq_obj_func(368, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode     BufferedDiCtrl_Start(BufferedDiCtrl *_this)                                                     { return bdaq_obj_func(369, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode     BufferedDiCtrl_Stop(BufferedDiCtrl *_this)                                                      { return bdaq_obj_func(370, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode     BufferedDiCtrl_GetData(BufferedDiCtrl *_this, int32 count, uint8 data[])                        { return bdaq_obj_func(371, (ErrorCode (BDAQCALL *)(void *, int32, uint8*)))(_this, count, data); }
   __inline void          BufferedDiCtrl_Release(BufferedDiCtrl *_this)                                                   {        bdaq_obj_func(372, (void (BDAQCALL *)(void *)))(_this);            }
   // property
   __inline void*         BufferedDiCtrl_getBuffer(BufferedDiCtrl *_this)                                                 { return bdaq_obj_get(373, void*)(_this);         }
   __inline int32         BufferedDiCtrl_getBufferCapacity(BufferedDiCtrl *_this)                                         { return bdaq_obj_get(374, int32)(_this);         }
   __inline ControlState  BufferedDiCtrl_getState(BufferedDiCtrl *_this)                                                  { return bdaq_obj_get(375, ControlState)(_this);  }
   __inline ScanPort*     BufferedDiCtrl_getScanPort(BufferedDiCtrl *_this)                                               { return bdaq_obj_get(376, ScanPort*)(_this);     }
   __inline ConvertClock* BufferedDiCtrl_getConvertClock(BufferedDiCtrl *_this)                                           { return bdaq_obj_get(377, ConvertClock*)(_this); }
   __inline ScanClock*    BufferedDiCtrl_getScanClock(BufferedDiCtrl *_this)                                              { return bdaq_obj_get(378, ScanClock*)(_this);    }
   __inline Trigger*      BufferedDiCtrl_getTrigger(BufferedDiCtrl *_this)                                                { return bdaq_obj_get(379, Trigger*)(_this);      }
   __inline int8          BufferedDiCtrl_getStreaming(BufferedDiCtrl *_this)                                              { return bdaq_obj_get(380, int8)(_this);          }
   __inline ErrorCode     BufferedDiCtrl_setStreaming(BufferedDiCtrl *_this, int8 value)                                  { return bdaq_obj_set(381, int8)(_this, value);   }

   // ----------------------------------------------------------
   // DO features (method index: 382~403)
   // ----------------------------------------------------------
   __inline int8           DoFeatures_getPortProgrammable(DoFeatures *_this)                                   { return bdaq_obj_get(382, int8 )(_this);                   }
   __inline int32          DoFeatures_getPortCount(DoFeatures *_this)                                          { return bdaq_obj_get(383, int32)(_this);                   }
   __inline ICollection*   DoFeatures_getPortsType(DoFeatures *_this)                                          { return bdaq_obj_get(384, ICollection*)(_this);            }
   __inline int8           DoFeatures_getDiSupported(DoFeatures *_this)                                        { return bdaq_obj_get(385, int8 )(_this);                   }
   __inline int8           DoFeatures_getDoSupported(DoFeatures *_this)                                        { return bdaq_obj_get(386, int8 )(_this);                   }
   __inline int32          DoFeatures_getChannelCountMax(DoFeatures *_this)                                    { return bdaq_obj_get(387, int32)(_this);                   }
   __inline ICollection*   DoFeatures_getDataMask(DoFeatures *_this)                                           { return bdaq_obj_get(388, ICollection*)(_this);            }
   // do freeze features                                                                                       
   __inline ICollection*   DoFeatures_getDoFreezeSignalSources(DoFeatures *_this)                              { return bdaq_obj_get(389, ICollection*)(_this);            }
   // do reflect Wdt features                                                             
   __inline void           DoFeatures_getDoReflectWdtFeedIntervalRange(DoFeatures *_this, MathInterval *value) { bdaq_obj_get_v1(390, void, MathInterval *)(_this, value); }
   // buffered do->basic features                                                         
   __inline int8           DoFeatures_getBufferedDoSupported(DoFeatures *_this)                                { return bdaq_obj_get(391, int8 )(_this);                   }
   __inline SamplingMethod DoFeatures_getSamplingMethod(DoFeatures *_this)                                     { return bdaq_obj_get(392, SamplingMethod )(_this);         }
   // buffered do->conversion clock features                                              
   __inline ICollection*   DoFeatures_getConvertClockSources(DoFeatures *_this)                                { return bdaq_obj_get(393, ICollection*)(_this);            }
   __inline void           DoFeatures_getConvertClockRange(DoFeatures *_this, MathInterval *value)             { bdaq_obj_get_v1(394, void, MathInterval *)(_this, value); }
   // buffered do->burst scan                                                             
   __inline int8           DoFeatures_getBurstScanSupported(DoFeatures *_this)                                 { return bdaq_obj_get(395, int8 )(_this);                   }
   __inline ICollection*   DoFeatures_getScanClockSources(DoFeatures *_this)                                   { return bdaq_obj_get(396, ICollection*)(_this);            }
   __inline void           DoFeatures_getScanClockRange(DoFeatures *_this, MathInterval *value)                { bdaq_obj_get_v1(397, void, MathInterval *)(_this, value); }
   __inline int32          DoFeatures_getScanCountMax(DoFeatures *_this)                                       { return bdaq_obj_get(398, int32)(_this);                   }
   // buffered do->trigger features                                                                            
   __inline int8           DoFeatures_getTriggerSupported(DoFeatures *_this)                                   { return bdaq_obj_get(399, int8 )(_this);                   }
   __inline int32          DoFeatures_getTriggerCount(DoFeatures *_this)                                       { return bdaq_obj_get(400, int32)(_this);                   }
   __inline ICollection*   DoFeatures_getTriggerSources(DoFeatures *_this)                                     { return bdaq_obj_get(401, ICollection*)(_this);            }
   __inline ICollection*   DoFeatures_getTriggerActions(DoFeatures *_this)                                     { return bdaq_obj_get(402, ICollection*)(_this);            }
   __inline void           DoFeatures_getTriggerDelayRange(DoFeatures *_this, MathInterval *value)             { bdaq_obj_get_v1(403, void, MathInterval *)(_this, value); }

   // ----------------------------------------------------------
   // InstantDoCtrl (method index: 404~425)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       InstantDoCtrl_Dispose(InstantDoCtrl *_this)                                                      { bdaq_obj_func(404, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       InstantDoCtrl_Cleanup(InstantDoCtrl *_this)                                                      { bdaq_obj_func(405, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  InstantDoCtrl_UpdateProperties(InstantDoCtrl *_this)                                             { return bdaq_obj_func(406, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       InstantDoCtrl_addRemovedListener(InstantDoCtrl *_this, DeviceEventListener * listener)           { bdaq_obj_func(407, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDoCtrl_removeRemovedListener(InstantDoCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(408, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDoCtrl_addReconnectedListener(InstantDoCtrl *_this, DeviceEventListener * listener)       { bdaq_obj_func(409, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDoCtrl_removeReconnectedListener(InstantDoCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(410, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDoCtrl_addPropertyChangedListener(InstantDoCtrl *_this, DeviceEventListener * listener)   { bdaq_obj_func(411, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDoCtrl_removePropertyChangedListener(InstantDoCtrl *_this, DeviceEventListener * listener){ bdaq_obj_func(412, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       InstantDoCtrl_getSelectedDevice(InstantDoCtrl *_this, DeviceInformation *x)                      { bdaq_obj_get_v1(413, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  InstantDoCtrl_setSelectedDevice(InstantDoCtrl *_this, DeviceInformation const *x)                { return bdaq_obj_set(414, DeviceInformation const *)(_this, x);            }
   __inline int8       InstantDoCtrl_getInitialized(InstantDoCtrl *_this)                                               { return bdaq_obj_get(415, int8)(_this);                                    }
   __inline int8       InstantDoCtrl_getCanEditProperty(InstantDoCtrl *_this)                                           { return bdaq_obj_get(416, int8)(_this);                                    }
   __inline HANDLE     InstantDoCtrl_getDevice(InstantDoCtrl *_this)                                                    { return bdaq_obj_get(417, HANDLE)(_this);                                  }
   __inline HANDLE     InstantDoCtrl_getModule(InstantDoCtrl *_this)                                                    { return bdaq_obj_get(418, HANDLE)(_this);                                  }
   __inline ICollection* InstantDoCtrl_getSupportedDevices(InstantDoCtrl *_this)                                        { return bdaq_obj_get(419, ICollection*)(_this);                            }
   __inline ICollection* InstantDoCtrl_getSupportedModes(InstantDoCtrl *_this)                                          { return bdaq_obj_get(420, ICollection*)(_this);                            }
   /* Methods derived from DioCtrlBase */
   __inline int32        InstantDoCtrl_getPortCount(InstantDoCtrl *_this)                                               { return bdaq_obj_get(421, int32)(_this);                                   }
   __inline ICollection* InstantDoCtrl_getPortDirection(InstantDoCtrl *_this)                                           { return bdaq_obj_get(422, ICollection*)(_this);                            }
   /* Methods derived from DoCtrlBase */ 
   __inline DoFeatures*  InstantDoCtrl_getFeatures(InstantDoCtrl *_this)                                                { return bdaq_obj_get(423, DoFeatures*)(_this);                             }
   /* Instant DO methods */
   __inline ErrorCode    InstantDoCtrl_WriteAny(InstantDoCtrl *_this, int32 portStart, int32 portCount, uint8 data[])   { return bdaq_obj_func(424, (ErrorCode (BDAQCALL *)(void *, int32, int32, uint8*)))(_this, portStart, portCount, data); }
   __inline ErrorCode    InstantDoCtrl_ReadAny(InstantDoCtrl *_this, int32 portStart, int32 portCount, uint8 data[])    { return bdaq_obj_func(425, (ErrorCode (BDAQCALL *)(void *, int32, int32, uint8*)))(_this, portStart, portCount, data); }

   // ----------------------------------------------------------
   // BufferedDoCtrl (method index: 426~469)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       BufferedDoCtrl_Dispose(BufferedDoCtrl *_this)                                                        { bdaq_obj_func(426, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       BufferedDoCtrl_Cleanup(BufferedDoCtrl *_this)                                                        { bdaq_obj_func(427, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  BufferedDoCtrl_UpdateProperties(BufferedDoCtrl *_this)                                               { return bdaq_obj_func(428, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       BufferedDoCtrl_addRemovedListener(BufferedDoCtrl *_this, DeviceEventListener * listener)             { bdaq_obj_func(429, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDoCtrl_removeRemovedListener(BufferedDoCtrl *_this, DeviceEventListener * listener)          { bdaq_obj_func(430, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDoCtrl_addReconnectedListener(BufferedDoCtrl *_this, DeviceEventListener * listener)         { bdaq_obj_func(431, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDoCtrl_removeReconnectedListener(BufferedDoCtrl *_this, DeviceEventListener * listener)      { bdaq_obj_func(432, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDoCtrl_addPropertyChangedListener(BufferedDoCtrl *_this, DeviceEventListener * listener)     { bdaq_obj_func(433, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDoCtrl_removePropertyChangedListener(BufferedDoCtrl *_this, DeviceEventListener * listener)  { bdaq_obj_func(434, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedDoCtrl_getSelectedDevice(BufferedDoCtrl *_this, DeviceInformation *x)                        { bdaq_obj_get_v1(435, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  BufferedDoCtrl_setSelectedDevice(BufferedDoCtrl *_this, DeviceInformation const *x)                  { return bdaq_obj_set(436, DeviceInformation const *)(_this, x);            }
   __inline int8       BufferedDoCtrl_getInitialized(BufferedDoCtrl *_this)                                                 { return bdaq_obj_get(437, int8)(_this);                                    }
   __inline int8       BufferedDoCtrl_getCanEditProperty(BufferedDoCtrl *_this)                                             { return bdaq_obj_get(438, int8)(_this);                                    }
   __inline HANDLE     BufferedDoCtrl_getDevice(BufferedDoCtrl *_this)                                                      { return bdaq_obj_get(439, HANDLE)(_this);                                  }
   __inline HANDLE     BufferedDoCtrl_getModule(BufferedDoCtrl *_this)                                                      { return bdaq_obj_get(440, HANDLE)(_this);                                  }
   __inline ICollection*  BufferedDoCtrl_getSupportedDevices(BufferedDoCtrl *_this)                                         { return bdaq_obj_get(441, ICollection*)(_this);                            }
   __inline ICollection*  BufferedDoCtrl_getSupportedModes(BufferedDoCtrl *_this)                                           { return bdaq_obj_get(442, ICollection*)(_this);                            }
   /* Methods derived from DioCtrlBase */                                                                                   
   __inline int32         BufferedDoCtrl_getPortCount(BufferedDoCtrl *_this)                                                { return bdaq_obj_get(443, int32)(_this);                                   }
   __inline ICollection*  BufferedDoCtrl_getPortDirection(BufferedDoCtrl *_this)                                            { return bdaq_obj_get(444, ICollection*)(_this);                            }
   /* Methods derived from DoCtrlBase */                                                                                  
   __inline DoFeatures*   BufferedDoCtrl_getFeatures(BufferedDoCtrl *_this)                                                 { return bdaq_obj_get(445, DoFeatures*)(_this);                             }
   /* Buffered DO methods */
   // event
   __inline void          BufferedDoCtrl_addDataTransmittedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener)    { bdaq_obj_func(446, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDoCtrl_removeDataTransmittedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener) { bdaq_obj_func(447, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDoCtrl_addUnderrunListener(BufferedDoCtrl *_this, BfdDoEventListener *listener)           { bdaq_obj_func(448, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDoCtrl_removeUnderrunListener(BufferedDoCtrl *_this, BfdDoEventListener *listener)        { bdaq_obj_func(449, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDoCtrl_addCacheEmptiedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener)       { bdaq_obj_func(450, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDoCtrl_removeCacheEmptiedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener)    { bdaq_obj_func(451, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDoCtrl_addTransitStoppedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener)     { bdaq_obj_func(452, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDoCtrl_removeTransitStoppedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener)  { bdaq_obj_func(453, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDoCtrl_addStoppedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener)            { bdaq_obj_func(454, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          BufferedDoCtrl_removeStoppedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener)         { bdaq_obj_func(455, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   // method           
   __inline ErrorCode     BufferedDoCtrl_Prepare(BufferedDoCtrl *_this)                                                     { return bdaq_obj_func(456, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode     BufferedDoCtrl_RunOnce(BufferedDoCtrl *_this)                                                     { return bdaq_obj_func(457, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode     BufferedDoCtrl_Start(BufferedDoCtrl *_this)                                                       { return bdaq_obj_func(458, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline ErrorCode     BufferedDoCtrl_Stop(BufferedDoCtrl *_this, int32 action)                                          { return bdaq_obj_func(459, (ErrorCode (BDAQCALL *)(void *, int32)))(_this,action);               }
   __inline ErrorCode     BufferedDoCtrl_SetData(BufferedDoCtrl *_this, int32 count, uint8 data[])                          { return bdaq_obj_func(460, (ErrorCode (BDAQCALL *)(void *, int32, uint8*)))(_this, count, data); }
   __inline void          BufferedDoCtrl_Release(BufferedDoCtrl *_this)                                                     { bdaq_obj_func(461, (void (BDAQCALL *)(void *)))(_this);                   }
   // property
   __inline void*         BufferedDoCtrl_getBuffer(BufferedDoCtrl *_this)                                                   { return bdaq_obj_get(462, void*)(_this);                                   }
   __inline int32         BufferedDoCtrl_getBufferCapacity(BufferedDoCtrl *_this)                                           { return bdaq_obj_get(463, int32)(_this);                                   }
   __inline ControlState  BufferedDoCtrl_getState(BufferedDoCtrl *_this)                                                    { return bdaq_obj_get(464, ControlState)(_this);                            }
   __inline ScanPort*     BufferedDoCtrl_getScanPort(BufferedDoCtrl *_this)                                                 { return bdaq_obj_get(465, ScanPort*)(_this);                               }
   __inline ConvertClock* BufferedDoCtrl_getConvertClock(BufferedDoCtrl *_this)                                             { return bdaq_obj_get(466, ConvertClock*)(_this);                           }
   __inline Trigger*      BufferedDoCtrl_getTrigger(BufferedDoCtrl *_this)                                                  { return bdaq_obj_get(467, Trigger*)(_this);                                }
   __inline int8          BufferedDoCtrl_getStreaming(BufferedDoCtrl *_this)                                                { return bdaq_obj_get(468, int8)(_this);                                    }
   __inline ErrorCode     BufferedDoCtrl_setStreaming(BufferedDoCtrl *_this, int8 value)                                    { return bdaq_obj_set(469, int8)(_this, value);                             }

   // ----------------------------------------------------------
   // Counter Capability Indexer (method index: 470~472)
   // ----------------------------------------------------------
   __inline void          CounterCapabilityIndexer_Dispose(CounterCapabilityIndexer *_this)                                 { bdaq_obj_func(470, (void (BDAQCALL *)(void *)))(_this); }
   __inline int32         CounterCapabilityIndexer_getCount(CounterCapabilityIndexer *_this)                                { return bdaq_obj_get(471, int32)(_this);                 }
   __inline ICollection*  CounterCapabilityIndexer_getItem(CounterCapabilityIndexer *_this, int32 channel)                  { return bdaq_obj_get(472, ICollection*)(_this);          }

   // ----------------------------------------------------------
   // Event Counter features (method index: 473~479)
   // ----------------------------------------------------------
   __inline int32  EventCounterFeatures_getChannelCountMax(EventCounterFeatures *_this)                                     { return bdaq_obj_get(473, int32)(_this);                     }
   __inline int32  EventCounterFeatures_getResolution(EventCounterFeatures *_this)                                          { return bdaq_obj_get(474, int32)(_this);                     }
   __inline int32  EventCounterFeatures_getDataSize(EventCounterFeatures *_this)                                            { return bdaq_obj_get(475, int32)(_this);                     }
   __inline CounterCapabilityIndexer*  EventCounterFeatures_getCapabilities(EventCounterFeatures *_this)                    { return bdaq_obj_get(476, CounterCapabilityIndexer*)(_this); }
   __inline int8         EventCounterFeatures_getNoiseFilterSupported(EventCounterFeatures *_this)                          { return bdaq_obj_get(477, int8)(_this);                      }
   __inline ICollection* EventCounterFeatures_getNoiseFilterOfChannels(EventCounterFeatures *_this)                         { return bdaq_obj_get(478, ICollection*)(_this);              }
   __inline void         EventCounterFeatures_getNoiseFilterBlockTimeRange(EventCounterFeatures *_this, MathInterval *value){ bdaq_obj_get_v1(479, void, MathInterval *)(_this, value);   } 

   // ----------------------------------------------------------
   // EventCounterCtrl (method index: 480~504)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void        EventCounterCtrl_Dispose(EventCounterCtrl *_this)                                                      { bdaq_obj_func(480, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void        EventCounterCtrl_Cleanup(EventCounterCtrl *_this)                                                      { bdaq_obj_func(481, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode   EventCounterCtrl_UpdateProperties(EventCounterCtrl *_this)                                             { return bdaq_obj_func(482, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void        EventCounterCtrl_addRemovedListener(EventCounterCtrl *_this, DeviceEventListener * listener)           { bdaq_obj_func(483, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        EventCounterCtrl_removeRemovedListener(EventCounterCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(484, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        EventCounterCtrl_addReconnectedListener(EventCounterCtrl *_this, DeviceEventListener * listener)       { bdaq_obj_func(485, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        EventCounterCtrl_removeReconnectedListener(EventCounterCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(486, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        EventCounterCtrl_addPropertyChangedListener(EventCounterCtrl *_this, DeviceEventListener * listener)   { bdaq_obj_func(487, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        EventCounterCtrl_removePropertyChangedListener(EventCounterCtrl *_this, DeviceEventListener * listener){ bdaq_obj_func(488, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        EventCounterCtrl_getSelectedDevice(EventCounterCtrl *_this, DeviceInformation *x)                      { bdaq_obj_get_v1(489, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode   EventCounterCtrl_setSelectedDevice(EventCounterCtrl *_this, DeviceInformation const *x)                { return bdaq_obj_set(490, DeviceInformation const *)(_this, x);            }
   __inline int8        EventCounterCtrl_getInitialized(EventCounterCtrl *_this)                                               { return bdaq_obj_get(491, int8)(_this);                                    }
   __inline int8        EventCounterCtrl_getCanEditProperty(EventCounterCtrl *_this)                                           { return bdaq_obj_get(492, int8)(_this);                                    }
   __inline HANDLE      EventCounterCtrl_getDevice(EventCounterCtrl *_this)                                                    { return bdaq_obj_get(493, HANDLE)(_this);                                  }
   __inline HANDLE      EventCounterCtrl_getModule(EventCounterCtrl *_this)                                                    { return bdaq_obj_get(494, HANDLE)(_this);                                  }
   __inline ICollection* EventCounterCtrl_getSupportedDevices(EventCounterCtrl *_this)                                         { return bdaq_obj_get(495, ICollection*)(_this);                            }
   __inline ICollection* EventCounterCtrl_getSupportedModes(EventCounterCtrl *_this)                                           { return bdaq_obj_get(496, ICollection*)(_this);                            }
   /* Methods derived from CntrCtrlBase */
   __inline int32        EventCounterCtrl_getChannel(EventCounterCtrl *_this)                                                  { return bdaq_obj_get(497, int32)(_this);                                   }
   __inline ErrorCode    EventCounterCtrl_setChannel(EventCounterCtrl *_this, int32 ch)                                        { return bdaq_obj_set(498, int32)(_this, ch);                               }
   __inline int8         EventCounterCtrl_getEnabled(EventCounterCtrl *_this)                                                  { return bdaq_obj_get(499, int8)(_this);                                    }
   __inline ErrorCode    EventCounterCtrl_setEnabled(EventCounterCtrl *_this, int8 enabled)                                    { return bdaq_obj_set(500, int8)(_this, enabled);                           }
   __inline int8         EventCounterCtrl_getRunning(EventCounterCtrl *_this)                                                  { return bdaq_obj_get(501, int8)(_this);                                    }
   /* Methods derived from CntrCtrlExt */
   __inline NoiseFilterChannel*   EventCounterCtrl_getNoiseFilter(EventCounterCtrl *_this)                                     { return bdaq_obj_get(502, NoiseFilterChannel*)(_this);                     }
   /* Event counter methods */
   __inline EventCounterFeatures* EventCounterCtrl_getFeatures(EventCounterCtrl *_this)                                        { return bdaq_obj_get(503, EventCounterFeatures*)(_this);                   }
   __inline int32                 EventCounterCtrl_getValue(EventCounterCtrl *_this)                                           { return bdaq_obj_get(504, int32)(_this);                                   }

   // ----------------------------------------------------------
   // Frequency meter features (method index: 505~512)
   // ----------------------------------------------------------
   __inline int32  FreqMeterFeatures_getChannelCountMax(FreqMeterFeatures *_this)                                      { return bdaq_obj_get(505, int32)(_this);                     }
   __inline int32  FreqMeterFeatures_getResolution(FreqMeterFeatures *_this)                                           { return bdaq_obj_get(506, int32)(_this);                     }
   __inline int32  FreqMeterFeatures_getDataSize(FreqMeterFeatures *_this)                                             { return bdaq_obj_get(507, int32)(_this);                     }
   __inline CounterCapabilityIndexer*  FreqMeterFeatures_getCapabilities(FreqMeterFeatures *_this)                     { return bdaq_obj_get(508, CounterCapabilityIndexer*)(_this); }
   __inline int8          FreqMeterFeatures_getNoiseFilterSupported(FreqMeterFeatures *_this)                          { return bdaq_obj_get(509, int8)(_this);                      }
   __inline ICollection*  FreqMeterFeatures_getNoiseFilterOfChannels(FreqMeterFeatures *_this)                         { return bdaq_obj_get(510, ICollection*)(_this);              }
   __inline void          FreqMeterFeatures_getNoiseFilterBlockTimeRange(FreqMeterFeatures *_this, MathInterval *value){ bdaq_obj_get_v1(511, void, MathInterval *)(_this, value);   } 
   __inline ICollection*  FreqMeterFeatures_getFmMethods(FreqMeterFeatures *_this)                                     { return bdaq_obj_get(512, ICollection*)(_this);              }

   // ----------------------------------------------------------
   // FreqMeterCtrl (method index: 513~541)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void        FreqMeterCtrl_Dispose(FreqMeterCtrl *_this)                                                      { bdaq_obj_func(513, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void        FreqMeterCtrl_Cleanup(FreqMeterCtrl *_this)                                                      { bdaq_obj_func(514, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode   FreqMeterCtrl_UpdateProperties(FreqMeterCtrl *_this)                                             { return bdaq_obj_func(515, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void        FreqMeterCtrl_addRemovedListener(FreqMeterCtrl *_this, DeviceEventListener * listener)           { bdaq_obj_func(516, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        FreqMeterCtrl_removeRemovedListener(FreqMeterCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(517, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        FreqMeterCtrl_addReconnectedListener(FreqMeterCtrl *_this, DeviceEventListener * listener)       { bdaq_obj_func(518, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        FreqMeterCtrl_removeReconnectedListener(FreqMeterCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(519, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        FreqMeterCtrl_addPropertyChangedListener(FreqMeterCtrl *_this, DeviceEventListener * listener)   { bdaq_obj_func(520, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        FreqMeterCtrl_removePropertyChangedListener(FreqMeterCtrl *_this, DeviceEventListener * listener){ bdaq_obj_func(521, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void        FreqMeterCtrl_getSelectedDevice(FreqMeterCtrl *_this, DeviceInformation *x)                      { bdaq_obj_get_v1(522, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode   FreqMeterCtrl_setSelectedDevice(FreqMeterCtrl *_this, DeviceInformation const *x)                { return bdaq_obj_set(523, DeviceInformation const *)(_this, x);            }
   __inline int8        FreqMeterCtrl_getInitialized(FreqMeterCtrl *_this)                                               { return bdaq_obj_get(524, int8)(_this);                                    }
   __inline int8        FreqMeterCtrl_getCanEditProperty(FreqMeterCtrl *_this)                                           { return bdaq_obj_get(525, int8)(_this);                                    }
   __inline HANDLE      FreqMeterCtrl_getDevice(FreqMeterCtrl *_this)                                                    { return bdaq_obj_get(526, HANDLE)(_this);                                  }
   __inline HANDLE      FreqMeterCtrl_getModule(FreqMeterCtrl *_this)                                                    { return bdaq_obj_get(527, HANDLE)(_this);                                  }
   __inline ICollection*  FreqMeterCtrl_getSupportedDevices(FreqMeterCtrl *_this)                                        { return bdaq_obj_get(528, ICollection*)(_this);                            }
   __inline ICollection*  FreqMeterCtrl_getSupportedModes(FreqMeterCtrl *_this)                                          { return bdaq_obj_get(529, ICollection*)(_this);                            }
   /* Methods derived from CntrCtrlBase */                                                                               
   __inline int32         FreqMeterCtrl_getChannel(FreqMeterCtrl *_this)                                                 { return bdaq_obj_get(530, int32)(_this);                                   }
   __inline ErrorCode     FreqMeterCtrl_setChannel(FreqMeterCtrl *_this, int32 ch)                                       { return bdaq_obj_set(531, int32)(_this, ch);                               }
   __inline int8          FreqMeterCtrl_getEnabled(FreqMeterCtrl *_this)                                                 { return bdaq_obj_get(532, int8)(_this);                                    }
   __inline ErrorCode     FreqMeterCtrl_setEnabled(FreqMeterCtrl *_this, int8 enabled)                                   { return bdaq_obj_set(533, int8)(_this, enabled);                           }
   __inline int8          FreqMeterCtrl_getRunning(FreqMeterCtrl *_this)                                                 { return bdaq_obj_get(534, int8)(_this);                                    }
   /* Methods derived from CntrCtrlExt */                                                                                
   __inline NoiseFilterChannel* FreqMeterCtrl_getNoiseFilter(FreqMeterCtrl *_this)                                       { return bdaq_obj_get(535, NoiseFilterChannel*)(_this);                     }
   /* Frequency meter methods */
   __inline FreqMeterFeatures*  FreqMeterCtrl_getFeatures(FreqMeterCtrl *_this)                                          { return bdaq_obj_get(536, FreqMeterFeatures*)(_this);                      }
   __inline double              FreqMeterCtrl_getValue(FreqMeterCtrl *_this)                                             { return bdaq_obj_get(537, double)(_this);                                  }
   __inline FreqMeasureMethod   FreqMeterCtrl_getMethod(FreqMeterCtrl *_this)                                            { return bdaq_obj_get(538, FreqMeasureMethod)(_this);                       }
   __inline ErrorCode           FreqMeterCtrl_setMethod(FreqMeterCtrl *_this, FreqMeasureMethod value)                   { return bdaq_obj_set(539, FreqMeasureMethod)(_this, value);                }
   __inline double              FreqMeterCtrl_getCollectionPeriod(FreqMeterCtrl *_this)                                  { return bdaq_obj_get(540, double)(_this);                                  }
   __inline ErrorCode           FreqMeterCtrl_setCollectionPeriod(FreqMeterCtrl *_this, double value)                    { return bdaq_obj_set(541, double)(_this, value);                           }

   // ----------------------------------------------------------
   // One shot features (method index: 542~549)
   // ----------------------------------------------------------
   __inline int32  OneShotFeatures_getChannelCountMax(OneShotFeatures *_this)                                        { return bdaq_obj_get(542, int32)(_this);                     }
   __inline int32  OneShotFeatures_getResolution(OneShotFeatures *_this)                                             { return bdaq_obj_get(543, int32)(_this);                     }
   __inline int32  OneShotFeatures_getDataSize(OneShotFeatures *_this)                                               { return bdaq_obj_get(544, int32)(_this);                     }
   __inline CounterCapabilityIndexer*  OneShotFeatures_getCapabilities(OneShotFeatures *_this)                       { return bdaq_obj_get(545, CounterCapabilityIndexer*)(_this); }
   __inline int8          OneShotFeatures_getNoiseFilterSupported(OneShotFeatures *_this)                            { return bdaq_obj_get(546, int8)(_this);                      }
   __inline ICollection*  OneShotFeatures_getNoiseFilterOfChannels(OneShotFeatures *_this)                           { return bdaq_obj_get(547, ICollection*)(_this);              }
   __inline void          OneShotFeatures_getNoiseFilterBlockTimeRange(OneShotFeatures *_this, MathInterval *value)  { bdaq_obj_get_v1(548, void, MathInterval *)(_this, value);   } 
   __inline void          OneShotFeatures_getDelayCountRange(OneShotFeatures *_this, MathInterval *value)            { bdaq_obj_get_v1(549, void, MathInterval *)(_this, value);   } 

   // ----------------------------------------------------------
   // OneShotCtrl (method index: 550~577)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       OneShotCtrl_Dispose(OneShotCtrl *_this)                                                        { bdaq_obj_func(550, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       OneShotCtrl_Cleanup(OneShotCtrl *_this)                                                        { bdaq_obj_func(551, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  OneShotCtrl_UpdateProperties(OneShotCtrl *_this)                                               { return bdaq_obj_func(552, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       OneShotCtrl_addRemovedListener(OneShotCtrl *_this, DeviceEventListener * listener)             { bdaq_obj_func(553, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       OneShotCtrl_removeRemovedListener(OneShotCtrl *_this, DeviceEventListener * listener)          { bdaq_obj_func(554, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       OneShotCtrl_addReconnectedListener(OneShotCtrl *_this, DeviceEventListener * listener)         { bdaq_obj_func(555, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       OneShotCtrl_removeReconnectedListener(OneShotCtrl *_this, DeviceEventListener * listener)      { bdaq_obj_func(556, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       OneShotCtrl_addPropertyChangedListener(OneShotCtrl *_this, DeviceEventListener * listener)     { bdaq_obj_func(557, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       OneShotCtrl_removePropertyChangedListener(OneShotCtrl *_this, DeviceEventListener * listener)  { bdaq_obj_func(558, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       OneShotCtrl_getSelectedDevice(OneShotCtrl *_this, DeviceInformation *x)                        { bdaq_obj_get_v1(559, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  OneShotCtrl_setSelectedDevice(OneShotCtrl *_this, DeviceInformation const *x)                  { return bdaq_obj_set(560, DeviceInformation const *)(_this, x);            }
   __inline int8       OneShotCtrl_getInitialized(OneShotCtrl *_this)                                                 { return bdaq_obj_get(561, int8)(_this);                                    }
   __inline int8       OneShotCtrl_getCanEditProperty(OneShotCtrl *_this)                                             { return bdaq_obj_get(562, int8)(_this);                                    }
   __inline HANDLE     OneShotCtrl_getDevice(OneShotCtrl *_this)                                                      { return bdaq_obj_get(563, HANDLE)(_this);                                  }
   __inline HANDLE     OneShotCtrl_getModule(OneShotCtrl *_this)                                                      { return bdaq_obj_get(564, HANDLE)(_this);                                  }
   __inline ICollection* OneShotCtrl_getSupportedDevices(OneShotCtrl *_this)                                          { return bdaq_obj_get(565, ICollection*)(_this);                            }
   __inline ICollection* OneShotCtrl_getSupportedModes(OneShotCtrl *_this)                                            { return bdaq_obj_get(566, ICollection*)(_this);                            }
   /* Methods derived from CntrCtrlBase */                                                                            
   __inline int32        OneShotCtrl_getChannel(OneShotCtrl *_this)                                                   { return bdaq_obj_get(567, int32)(_this);                                   }
   __inline ErrorCode    OneShotCtrl_setChannel(OneShotCtrl *_this, int32 ch)                                         { return bdaq_obj_set(568, int32)(_this, ch);                               }
   __inline int8         OneShotCtrl_getEnabled(OneShotCtrl *_this)                                                   { return bdaq_obj_get(569, int8)(_this);                                    }
   __inline ErrorCode    OneShotCtrl_setEnabled(OneShotCtrl *_this, int8 enabled)                                     { return bdaq_obj_set(570, int8)(_this, enabled);                           }
   __inline int8         OneShotCtrl_getRunning(OneShotCtrl *_this)                                                   { return bdaq_obj_get(571, int8)(_this);                                    }
   /* Methods derived from CntrCtrlExt */                                                                             
   __inline NoiseFilterChannel* OneShotCtrl_getNoiseFilter(OneShotCtrl *_this)                                        { return bdaq_obj_get(572, NoiseFilterChannel*)(_this);                     }
   /* one shot methods */
   __inline void             OneShotCtrl_addOneShotListener(OneShotCtrl *_this, CntrEventListener * listener)         { bdaq_obj_func(573, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void             OneShotCtrl_removeOneShotListener(OneShotCtrl *_this, CntrEventListener * listener)      { bdaq_obj_func(574, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline OneShotFeatures* OneShotCtrl_getFeatures(OneShotCtrl *_this)                                              { return bdaq_obj_get(575, OneShotFeatures*)(_this);                        }
   __inline int32            OneShotCtrl_getDelayCount(OneShotCtrl *_this)                                            { return bdaq_obj_get(576, int32)(_this);                                   }
   __inline ErrorCode        OneShotCtrl_setDelayCount(OneShotCtrl *_this, int32 value)                               { return bdaq_obj_set(577, int32)(_this, value);                            }

   // ----------------------------------------------------------
   // Timer/Pulse features (method index: 578~586)
   // ----------------------------------------------------------
   __inline int32  TimerPulseFeatures_getChannelCountMax(TimerPulseFeatures *_this)                                     { return bdaq_obj_get(578, int32)(_this);                     }
   __inline int32  TimerPulseFeatures_getResolution(TimerPulseFeatures *_this)                                          { return bdaq_obj_get(579, int32)(_this);                     }
   __inline int32  TimerPulseFeatures_getDataSize(TimerPulseFeatures *_this)                                            { return bdaq_obj_get(580, int32)(_this);                     }
   __inline CounterCapabilityIndexer*  TimerPulseFeatures_getCapabilities(TimerPulseFeatures *_this)                    { return bdaq_obj_get(581, CounterCapabilityIndexer*)(_this); }
   __inline int8         TimerPulseFeatures_getNoiseFilterSupported(TimerPulseFeatures *_this)                          { return bdaq_obj_get(582, int8)(_this);                      }
   __inline ICollection* TimerPulseFeatures_getNoiseFilterOfChannels(TimerPulseFeatures *_this)                         { return bdaq_obj_get(583, ICollection*)(_this);              }
   __inline void         TimerPulseFeatures_getNoiseFilterBlockTimeRange(TimerPulseFeatures *_this, MathInterval *value){ bdaq_obj_get_v1(584, void, MathInterval *)(_this, value);   } 
   __inline void         TimerPulseFeatures_getTimerFrequencyRange(TimerPulseFeatures *_this, MathInterval *value)      { bdaq_obj_get_v1(585, void, MathInterval *)(_this, value);   }
   __inline int8         TimerPulseFeatures_getTimerEventSupported(TimerPulseFeatures *_this)                           { return bdaq_obj_get(586, int8)(_this);                      }

   // ----------------------------------------------------------
   // TimerPulseCtrl (method index: 587~614)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       TimerPulseCtrl_Dispose(TimerPulseCtrl *_this)                                                      { bdaq_obj_func(587, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       TimerPulseCtrl_Cleanup(TimerPulseCtrl *_this)                                                      { bdaq_obj_func(588, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  TimerPulseCtrl_UpdateProperties(TimerPulseCtrl *_this)                                             { return bdaq_obj_func(589, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       TimerPulseCtrl_addRemovedListener(TimerPulseCtrl *_this, DeviceEventListener * listener)           { bdaq_obj_func(590, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       TimerPulseCtrl_removeRemovedListener(TimerPulseCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(591, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       TimerPulseCtrl_addReconnectedListener(TimerPulseCtrl *_this, DeviceEventListener * listener)       { bdaq_obj_func(592, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       TimerPulseCtrl_removeReconnectedListener(TimerPulseCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(593, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       TimerPulseCtrl_addPropertyChangedListener(TimerPulseCtrl *_this, DeviceEventListener * listener)   { bdaq_obj_func(594, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       TimerPulseCtrl_removePropertyChangedListener(TimerPulseCtrl *_this, DeviceEventListener * listener){ bdaq_obj_func(595, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       TimerPulseCtrl_getSelectedDevice(TimerPulseCtrl *_this, DeviceInformation *x)                      { bdaq_obj_get_v1(596, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  TimerPulseCtrl_setSelectedDevice(TimerPulseCtrl *_this, DeviceInformation const *x)                { return bdaq_obj_set(597, DeviceInformation const *)(_this, x);            }
   __inline int8       TimerPulseCtrl_getInitialized(TimerPulseCtrl *_this)                                               { return bdaq_obj_get(598, int8)(_this);                                    }
   __inline int8       TimerPulseCtrl_getCanEditProperty(TimerPulseCtrl *_this)                                           { return bdaq_obj_get(599, int8)(_this);                                    }
   __inline HANDLE     TimerPulseCtrl_getDevice(TimerPulseCtrl *_this)                                                    { return bdaq_obj_get(600, HANDLE)(_this);                                  }
   __inline HANDLE     TimerPulseCtrl_getModule(TimerPulseCtrl *_this)                                                    { return bdaq_obj_get(601, HANDLE)(_this);                                  }
   __inline ICollection*  TimerPulseCtrl_getSupportedDevices(TimerPulseCtrl *_this)                                       { return bdaq_obj_get(602, ICollection*)(_this);                            }
   __inline ICollection*  TimerPulseCtrl_getSupportedModes(TimerPulseCtrl *_this)                                         { return bdaq_obj_get(603, ICollection*)(_this);                            }
   /* Methods derived from CntrCtrlBase */                                                                                
   __inline int32         TimerPulseCtrl_getChannel(TimerPulseCtrl *_this)                                                { return bdaq_obj_get(604, int32)(_this);                                   }
   __inline ErrorCode     TimerPulseCtrl_setChannel(TimerPulseCtrl *_this, int32 ch)                                      { return bdaq_obj_set(605, int32)(_this, ch);                               }
   __inline int8          TimerPulseCtrl_getEnabled(TimerPulseCtrl *_this)                                                { return bdaq_obj_get(606, int8)(_this);                                    }
   __inline ErrorCode     TimerPulseCtrl_setEnabled(TimerPulseCtrl *_this, int8 enabled)                                  { return bdaq_obj_set(607, int8)(_this, enabled);                           }
   __inline int8          TimerPulseCtrl_getRunning(TimerPulseCtrl *_this)                                                { return bdaq_obj_get(608, int8)(_this);                                    }
   /* Methods derived from CntrCtrlExt */                                                                                 
   __inline NoiseFilterChannel* TimerPulseCtrl_getNoiseFilter(TimerPulseCtrl *_this)                                      { return bdaq_obj_get(609, NoiseFilterChannel*)(_this);                     }
   /* timer pulse methods */
   __inline void          TimerPulseCtrl_addTimerTickListener(TimerPulseCtrl *_this, CntrEventListener * listener)        { bdaq_obj_func(610, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void          TimerPulseCtrl_removeTimerTickListener(TimerPulseCtrl *_this, CntrEventListener * listener)     { bdaq_obj_func(611, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline TimerPulseFeatures*  TimerPulseCtrl_getFeatures(TimerPulseCtrl *_this)                                        { return bdaq_obj_get(612, TimerPulseFeatures*)(_this);                     }
   __inline double        TimerPulseCtrl_getFrequency(TimerPulseCtrl *_this)                                              { return bdaq_obj_get(613, double)(_this);                                  }
   __inline ErrorCode     TimerPulseCtrl_setFrequency(TimerPulseCtrl *_this, double value)                                { return bdaq_obj_set(614, double)(_this, value);                           }

   // ----------------------------------------------------------
   // Pulse width meter features (method index: 615~623)
   // ----------------------------------------------------------
   __inline int32  PwMeterFeatures_getChannelCountMax(PwMeterFeatures *_this)                                        { return bdaq_obj_get(615, int32)(_this);                     }
   __inline int32  PwMeterFeatures_getResolution(PwMeterFeatures *_this)                                             { return bdaq_obj_get(616, int32)(_this);                     }
   __inline int32  PwMeterFeatures_getDataSize(PwMeterFeatures *_this)                                               { return bdaq_obj_get(617, int32)(_this);                     }
   __inline CounterCapabilityIndexer*  PwMeterFeatures_getCapabilities(PwMeterFeatures *_this)                       { return bdaq_obj_get(618, CounterCapabilityIndexer*)(_this); }
   __inline int8         PwMeterFeatures_getNoiseFilterSupported(PwMeterFeatures *_this)                             { return bdaq_obj_get(619, int8)(_this);                      }
   __inline ICollection* PwMeterFeatures_getNoiseFilterOfChannels(PwMeterFeatures *_this)                            { return bdaq_obj_get(620, ICollection*)(_this);              }
   __inline void         PwMeterFeatures_getNoiseFilterBlockTimeRange(PwMeterFeatures *_this, MathInterval *value)   { bdaq_obj_get_v1(621, void, MathInterval *)(_this, value);   }  
   __inline ICollection* PwMeterFeatures_getPwmCascadeGroup(PwMeterFeatures *_this)                                  { return bdaq_obj_get(622, ICollection*)(_this);              }
   __inline int8         PwMeterFeatures_getOverflowEventSupported(PwMeterFeatures *_this)                           { return bdaq_obj_get(623, int8)(_this);                      }

   // ----------------------------------------------------------
   // PwMeterCtrl (method index: 624~650)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       PwMeterCtrl_Dispose(PwMeterCtrl *_this)                                                       { bdaq_obj_func(624, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       PwMeterCtrl_Cleanup(PwMeterCtrl *_this)                                                       { bdaq_obj_func(625, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  PwMeterCtrl_UpdateProperties(PwMeterCtrl *_this)                                              { return bdaq_obj_func(626, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       PwMeterCtrl_addRemovedListener(PwMeterCtrl *_this, DeviceEventListener * listener)            { bdaq_obj_func(627, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwMeterCtrl_removeRemovedListener(PwMeterCtrl *_this, DeviceEventListener * listener)         { bdaq_obj_func(628, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwMeterCtrl_addReconnectedListener(PwMeterCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(629, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwMeterCtrl_removeReconnectedListener(PwMeterCtrl *_this, DeviceEventListener * listener)     { bdaq_obj_func(630, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwMeterCtrl_addPropertyChangedListener(PwMeterCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(631, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwMeterCtrl_removePropertyChangedListener(PwMeterCtrl *_this, DeviceEventListener * listener) { bdaq_obj_func(632, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwMeterCtrl_getSelectedDevice(PwMeterCtrl *_this, DeviceInformation *x)                       { bdaq_obj_get_v1(633, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  PwMeterCtrl_setSelectedDevice(PwMeterCtrl *_this, DeviceInformation const *x)                 { return bdaq_obj_set(634, DeviceInformation const *)(_this, x);            }
   __inline int8       PwMeterCtrl_getInitialized(PwMeterCtrl *_this)                                                { return bdaq_obj_get(635, int8)(_this);                                    }
   __inline int8       PwMeterCtrl_getCanEditProperty(PwMeterCtrl *_this)                                            { return bdaq_obj_get(636, int8)(_this);                                    }
   __inline HANDLE     PwMeterCtrl_getDevice(PwMeterCtrl *_this)                                                     { return bdaq_obj_get(637, HANDLE)(_this);                                  }
   __inline HANDLE     PwMeterCtrl_getModule(PwMeterCtrl *_this)                                                     { return bdaq_obj_get(638, HANDLE)(_this);                                  }
   __inline ICollection*  PwMeterCtrl_getSupportedDevices(PwMeterCtrl *_this)                                        { return bdaq_obj_get(639, ICollection*)(_this);                            }
   __inline ICollection*  PwMeterCtrl_getSupportedModes(PwMeterCtrl *_this)                                          { return bdaq_obj_get(640, ICollection*)(_this);                            }
   /* Methods derived from CntrCtrlBase */                                                                           
   __inline int32      PwMeterCtrl_getChannel(PwMeterCtrl *_this)                                                    { return bdaq_obj_get(641, int32)(_this);                                   }
   __inline ErrorCode  PwMeterCtrl_setChannel(PwMeterCtrl *_this, int32 ch)                                          { return bdaq_obj_set(642, int32)(_this, ch);                               }
   __inline int8       PwMeterCtrl_getEnabled(PwMeterCtrl *_this)                                                    { return bdaq_obj_get(643, int8)(_this);                                    }
   __inline ErrorCode  PwMeterCtrl_setEnabled(PwMeterCtrl *_this, int8 enabled)                                      { return bdaq_obj_set(644, int8)(_this, enabled);                           }
   __inline int8       PwMeterCtrl_getRunning(PwMeterCtrl *_this)                                                    { return bdaq_obj_get(645, int8)(_this);                                    }
   /* Methods derived from CntrCtrlExt */                                                                            
   __inline NoiseFilterChannel*  PwMeterCtrl_getNoiseFilter(PwMeterCtrl *_this)                                      { return bdaq_obj_get(646, NoiseFilterChannel*)(_this);                     }
   /* Pulse width meter methods */
   __inline void       PwMeterCtrl_addOverflowListener(PwMeterCtrl *_this, CntrEventListener * listener)             { bdaq_obj_func(647, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwMeterCtrl_removeOverflowListener(PwMeterCtrl *_this, CntrEventListener * listener)          { bdaq_obj_func(648, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline PwMeterFeatures*  PwMeterCtrl_getFeatures(PwMeterCtrl *_this)                                            { return bdaq_obj_get(649, PwMeterFeatures*)(_this);                        }
   __inline void       PwMeterCtrl_getValue(PwMeterCtrl *_this, PulseWidth *width)                                   { bdaq_obj_get_v1(650, void, PulseWidth *)(_this, width);                   }

   // ----------------------------------------------------------
   // Pulse width modulator features (method index: 651~659)
   // ----------------------------------------------------------
   __inline int32  PwModulatorFeatures_getChannelCountMax(PwModulatorFeatures *_this)                                { return bdaq_obj_get(651, int32)(_this);                     }
   __inline int32  PwModulatorFeatures_getResolution(PwModulatorFeatures *_this)                                     { return bdaq_obj_get(652, int32)(_this);                     }
   __inline int32  PwModulatorFeatures_getDataSize(PwModulatorFeatures *_this)                                       { return bdaq_obj_get(653, int32)(_this);                     }
   __inline CounterCapabilityIndexer*  PwModulatorFeatures_getCapabilities(PwModulatorFeatures *_this)               { return bdaq_obj_get(654, CounterCapabilityIndexer*)(_this); }
   __inline int8   PwModulatorFeatures_getNoiseFilterSupported(PwModulatorFeatures *_this)                           { return bdaq_obj_get(655, int8)(_this);                      }
   __inline ICollection*  PwModulatorFeatures_getNoiseFilterOfChannels(PwModulatorFeatures *_this)                   { return bdaq_obj_get(656, ICollection*)(_this);              }
   __inline void   PwModulatorFeatures_getNoiseFilterBlockTimeRange(PwModulatorFeatures *_this, MathInterval *value) { bdaq_obj_get_v1(657, void, MathInterval *)(_this, value);   } 
   __inline void   PwModulatorFeatures_getHiPeriodRange(PwModulatorFeatures *_this, MathInterval *value)             { bdaq_obj_get_v1(658, void, MathInterval *)(_this, value);   } 
   __inline void   PwModulatorFeatures_getLoPeriodRange(PwModulatorFeatures *_this, MathInterval *value)             { bdaq_obj_get_v1(659, void, MathInterval *)(_this, value);   } 

   // ----------------------------------------------------------
   // PwModulatorCtrl (method index: 660~685)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       PwModulatorCtrl_Dispose(PwModulatorCtrl *_this)                                                      { bdaq_obj_func(660, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       PwModulatorCtrl_Cleanup(PwModulatorCtrl *_this)                                                      { bdaq_obj_func(661, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  PwModulatorCtrl_UpdateProperties(PwModulatorCtrl *_this)                                             { return bdaq_obj_func(662, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       PwModulatorCtrl_addRemovedListener(PwModulatorCtrl *_this, DeviceEventListener * listener)           { bdaq_obj_func(663, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwModulatorCtrl_removeRemovedListener(PwModulatorCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(664, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwModulatorCtrl_addReconnectedListener(PwModulatorCtrl *_this, DeviceEventListener * listener)       { bdaq_obj_func(665, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwModulatorCtrl_removeReconnectedListener(PwModulatorCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(666, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwModulatorCtrl_addPropertyChangedListener(PwModulatorCtrl *_this, DeviceEventListener * listener)   { bdaq_obj_func(667, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwModulatorCtrl_removePropertyChangedListener(PwModulatorCtrl *_this, DeviceEventListener * listener){ bdaq_obj_func(668, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       PwModulatorCtrl_getSelectedDevice(PwModulatorCtrl *_this, DeviceInformation *x)                      { bdaq_obj_get_v1(669, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  PwModulatorCtrl_setSelectedDevice(PwModulatorCtrl *_this, DeviceInformation const *x)                { return bdaq_obj_set(670, DeviceInformation const *)(_this, x);            }
   __inline int8       PwModulatorCtrl_getInitialized(PwModulatorCtrl *_this)                                               { return bdaq_obj_get(671, int8)(_this);                                    }
   __inline int8       PwModulatorCtrl_getCanEditProperty(PwModulatorCtrl *_this)                                           { return bdaq_obj_get(672, int8)(_this);                                    }
   __inline HANDLE     PwModulatorCtrl_getDevice(PwModulatorCtrl *_this)                                                    { return bdaq_obj_get(673, HANDLE)(_this);                                  }
   __inline HANDLE     PwModulatorCtrl_getModule(PwModulatorCtrl *_this)                                                    { return bdaq_obj_get(674, HANDLE)(_this);                                  }
   __inline ICollection*  PwModulatorCtrl_getSupportedDevices(PwModulatorCtrl *_this)                                       { return bdaq_obj_get(675, ICollection*)(_this);                            }
   __inline ICollection*  PwModulatorCtrl_getSupportedModes(PwModulatorCtrl *_this)                                         { return bdaq_obj_get(676, ICollection*)(_this);                            }
   /* Methods derived from CntrCtrlBase */                                                                                  
   __inline int32      PwModulatorCtrl_getChannel(PwModulatorCtrl *_this)                                                   { return bdaq_obj_get(677, int32)(_this);                                   }
   __inline ErrorCode  PwModulatorCtrl_setChannel(PwModulatorCtrl *_this, int32 ch)                                         { return bdaq_obj_set(678, int32)(_this, ch);                               }
   __inline int8       PwModulatorCtrl_getEnabled(PwModulatorCtrl *_this)                                                   { return bdaq_obj_get(679, int8)(_this);                                    }
   __inline ErrorCode  PwModulatorCtrl_setEnabled(PwModulatorCtrl *_this, int8 enabled)                                     { return bdaq_obj_set(680, int8)(_this, enabled);                           }
   __inline int8       PwModulatorCtrl_getRunning(PwModulatorCtrl *_this)                                                   { return bdaq_obj_get(681, int8)(_this);                                    }
   /* Methods derived from CntrCtrlExt */                                                                                   
   __inline NoiseFilterChannel*  PwModulatorCtrl_getNoiseFilter(PwModulatorCtrl *_this)                                     { return bdaq_obj_get(682, NoiseFilterChannel*)(_this);                     }
   /* Pulse width modulator methods */
   __inline PwModulatorFeatures* PwModulatorCtrl_getFeatures(PwModulatorCtrl *_this)                                        { return bdaq_obj_get(683, PwModulatorFeatures*)(_this);                    }
   __inline void       PwModulatorCtrl_getPulseWidth(PwModulatorCtrl *_this, PulseWidth *width)                             { bdaq_obj_get_v1(684, void, PulseWidth *)(_this, width);                   } 
   __inline ErrorCode  PwModulatorCtrl_setPulseWidth(PwModulatorCtrl *_this, PulseWidth *width)                             { return bdaq_obj_set(685, PulseWidth *)(_this, width);                     } 

   // ----------------------------------------------------------
   // Up-Down counter features (method index: 686~695)
   // ----------------------------------------------------------
   __inline int32  UdCounterFeatures_getChannelCountMax(UdCounterFeatures *_this)                                        { return bdaq_obj_get(686, int32)(_this);                     }
   __inline int32  UdCounterFeatures_getResolution(UdCounterFeatures *_this)                                             { return bdaq_obj_get(687, int32)(_this);                     }
   __inline int32  UdCounterFeatures_getDataSize(UdCounterFeatures *_this)                                               { return bdaq_obj_get(688, int32)(_this);                     }
   __inline CounterCapabilityIndexer*  UdCounterFeatures_getCapabilities(UdCounterFeatures *_this)                       { return bdaq_obj_get(689, CounterCapabilityIndexer*)(_this); }
   __inline int8          UdCounterFeatures_getNoiseFilterSupported(UdCounterFeatures *_this)                            { return bdaq_obj_get(690, int8)(_this);                      }
   __inline ICollection*  UdCounterFeatures_getNoiseFilterOfChannels(UdCounterFeatures *_this)                           { return bdaq_obj_get(691, ICollection*)(_this);              }
   __inline void          UdCounterFeatures_getNoiseFilterBlockTimeRange(UdCounterFeatures *_this, MathInterval *value)  { bdaq_obj_get_v1(692, void, MathInterval *)(_this, value);   } 
   __inline ICollection*  UdCounterFeatures_getCountingTypes(UdCounterFeatures *_this)                                   { return bdaq_obj_get(693, ICollection*)(_this);              }
   __inline ICollection*  UdCounterFeatures_getInitialValues(UdCounterFeatures *_this)                                   { return bdaq_obj_get(694, ICollection*)(_this);              }
   __inline ICollection*  UdCounterFeatures_getSnapEventSources(UdCounterFeatures *_this)                                { return bdaq_obj_get(695, ICollection*)(_this);              }

   // ----------------------------------------------------------
   // UdCounterCtrl (method index: 696~734)
   // ----------------------------------------------------------
   /* Methods derived from DeviceCtrlBase */
   __inline void       UdCounterCtrl_Dispose(UdCounterCtrl *_this)                                                      { bdaq_obj_func(696, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline void       UdCounterCtrl_Cleanup(UdCounterCtrl *_this)                                                      { bdaq_obj_func(697, (void (BDAQCALL *)(void *)))(_this);                   }
   __inline ErrorCode  UdCounterCtrl_UpdateProperties(UdCounterCtrl *_this)                                             { return bdaq_obj_func(698, (ErrorCode (BDAQCALL *)(void *)))(_this);       }
   __inline void       UdCounterCtrl_addRemovedListener(UdCounterCtrl *_this, DeviceEventListener * listener)           { bdaq_obj_func(699, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       UdCounterCtrl_removeRemovedListener(UdCounterCtrl *_this, DeviceEventListener * listener)        { bdaq_obj_func(700, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       UdCounterCtrl_addReconnectedListener(UdCounterCtrl *_this, DeviceEventListener * listener)       { bdaq_obj_func(701, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       UdCounterCtrl_removeReconnectedListener(UdCounterCtrl *_this, DeviceEventListener * listener)    { bdaq_obj_func(702, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       UdCounterCtrl_addPropertyChangedListener(UdCounterCtrl *_this, DeviceEventListener * listener)   { bdaq_obj_func(703, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       UdCounterCtrl_removePropertyChangedListener(UdCounterCtrl *_this, DeviceEventListener * listener){ bdaq_obj_func(704, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       UdCounterCtrl_getSelectedDevice(UdCounterCtrl *_this, DeviceInformation *x)                      { bdaq_obj_get_v1(705, void, DeviceInformation *)(_this, x);                }
   __inline ErrorCode  UdCounterCtrl_setSelectedDevice(UdCounterCtrl *_this, DeviceInformation const *x)                { return bdaq_obj_set(706, DeviceInformation const *)(_this, x);            }
   __inline int8       UdCounterCtrl_getInitialized(UdCounterCtrl *_this)                                               { return bdaq_obj_get(707, int8)(_this);                                    }
   __inline int8       UdCounterCtrl_getCanEditProperty(UdCounterCtrl *_this)                                           { return bdaq_obj_get(708, int8)(_this);                                    }
   __inline HANDLE     UdCounterCtrl_getDevice(UdCounterCtrl *_this)                                                    { return bdaq_obj_get(709, HANDLE)(_this);                                  }
   __inline HANDLE     UdCounterCtrl_getModule(UdCounterCtrl *_this)                                                    { return bdaq_obj_get(710, HANDLE)(_this);                                  }
   __inline ICollection*  UdCounterCtrl_getSupportedDevices(UdCounterCtrl *_this)                                       { return bdaq_obj_get(711, ICollection*)(_this);                            }
   __inline ICollection*  UdCounterCtrl_getSupportedModes(UdCounterCtrl *_this)                                         { return bdaq_obj_get(712, ICollection*)(_this);                            }
   /* Methods derived from CntrCtrlBase */                                                                              
   __inline int32      UdCounterCtrl_getChannel(UdCounterCtrl *_this)                                                   { return bdaq_obj_get(713, int32)(_this);                                   }
   __inline ErrorCode  UdCounterCtrl_setChannel(UdCounterCtrl *_this, int32 ch)                                         { return bdaq_obj_set(714, int32)(_this, ch);                               }
   __inline int8       UdCounterCtrl_getEnabled(UdCounterCtrl *_this)                                                   { return bdaq_obj_get(715, int8)(_this);                                    }
   __inline ErrorCode  UdCounterCtrl_setEnabled(UdCounterCtrl *_this, int8 enabled)                                     { return bdaq_obj_set(716, int8)(_this, enabled);                           }
   __inline int8       UdCounterCtrl_getRunning(UdCounterCtrl *_this)                                                   { return bdaq_obj_get(717, int8)(_this);                                    }
   /* Methods derived from CntrCtrlExt */                                                                               
   __inline NoiseFilterChannel*  UdCounterCtrl_getNoiseFilter(UdCounterCtrl *_this)                                     { return bdaq_obj_get(718, NoiseFilterChannel*)(_this);                     }
   /* up-down counter methods */
   __inline void       UdCounterCtrl_addUdCntrEventListener(UdCounterCtrl *_this, UdCntrEventListener * listener)       { bdaq_obj_func(719, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       UdCounterCtrl_removeUdCntrEventListener(UdCounterCtrl *_this, UdCntrEventListener * listener)    { bdaq_obj_func(720, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline ErrorCode  UdCounterCtrl_SnapStart(UdCounterCtrl *_this, int32 srcId)                                       { return bdaq_obj_func(721, (ErrorCode (BDAQCALL *)(void *, int32)))(_this, srcId);       }
   __inline ErrorCode  UdCounterCtrl_SnapStop(UdCounterCtrl *_this, int32 srcId)                                        { return bdaq_obj_func(722, (ErrorCode (BDAQCALL *)(void *, int32)))(_this, srcId);       }
   __inline ErrorCode  UdCounterCtrl_CompareSetTable(UdCounterCtrl *_this, int32 count, int32 *table)                   { return bdaq_obj_func(723, (ErrorCode (BDAQCALL *)(void *, int32, int32*)))(_this, count, table);                  }
   __inline ErrorCode  UdCounterCtrl_CompareSetInterval(UdCounterCtrl *_this, int32 start, int32 increment,int32 count) { return bdaq_obj_func(724, (ErrorCode (BDAQCALL *)(void *, int32, int32, int32)))(_this, start, increment, count); }
   __inline ErrorCode  UdCounterCtrl_CompareClear(UdCounterCtrl *_this)                                                 { return bdaq_obj_func(725, (ErrorCode (BDAQCALL *)(void *)))(_this); }
   __inline ErrorCode  UdCounterCtrl_ValueReset(UdCounterCtrl *_this)                                                   { return bdaq_obj_func(726, (ErrorCode (BDAQCALL *)(void *)))(_this); }

   __inline UdCounterFeatures*  UdCounterCtrl_getFeatures(UdCounterCtrl *_this)                                         { return bdaq_obj_get(727, UdCounterFeatures*)(_this);        }
   __inline int32               UdCounterCtrl_getValue(UdCounterCtrl *_this)                                            { return bdaq_obj_get(728, int32)(_this);                     }
   __inline SignalCountingType  UdCounterCtrl_getCountingType(UdCounterCtrl *_this)                                     { return bdaq_obj_get(729, SignalCountingType)(_this);        }
   __inline ErrorCode           UdCounterCtrl_setCountingType(UdCounterCtrl *_this, SignalCountingType value)           { return bdaq_obj_set(730, SignalCountingType)(_this, value); }
   __inline int32               UdCounterCtrl_getInitialValue(UdCounterCtrl *_this)                                     { return bdaq_obj_get(731, int32)(_this);                     }
   __inline ErrorCode           UdCounterCtrl_setInitialValue(UdCounterCtrl *_this, int32 value)                        { return bdaq_obj_set(732, int32)(_this, value);              }
   __inline int32               UdCounterCtrl_getResetTimesByIndex(UdCounterCtrl *_this)                                { return bdaq_obj_get(733, int32)(_this);                     }
   __inline ErrorCode           UdCounterCtrl_setResetTimesByIndex(UdCounterCtrl *_this, int32 value)                   { return bdaq_obj_set(734, int32)(_this, value);              }
   
   __inline ErrorCode    InstantDiCtrl_ReadBit(InstantDiCtrl *_this, int32 port, int32 bit, uint8* data)    { return bdaq_obj_func(735, (ErrorCode (BDAQCALL *)(void *, int32, int32, uint8*)))(_this, port, bit, data); }
   __inline ErrorCode    InstantDoCtrl_WriteBit(InstantDoCtrl *_this, int32 port, int32 bit, uint8 data)   { return bdaq_obj_func(736, (ErrorCode (BDAQCALL *)(void *, int32, int32, uint8)))(_this, port, bit, data); }
   __inline ErrorCode    InstantDoCtrl_ReadBit(InstantDoCtrl *_this, int32 port, int32 bit, uint8* data)    { return bdaq_obj_func(737, (ErrorCode (BDAQCALL *)(void *, int32, int32, uint8*)))(_this, port, bit, data); }

   __inline void       BufferedAiCtrl_addBurnOutListener(BufferedAiCtrl *_this, BfdAiEventListener *listener)             { bdaq_obj_func(738, (void (BDAQCALL *)(void *, void *)))(_this, listener); }
   __inline void       BufferedAiCtrl_removeBurnOutListener(BufferedAiCtrl *_this, BfdAiEventListener *listener)          { bdaq_obj_func(739, (void (BDAQCALL *)(void *, void *)))(_this, listener); }

#  undef bdaq_obj_func
#  undef bdaq_obj_set
#  undef bdaq_obj_get
#  undef bdaq_obj_get_v1

#  endif

#  else // Non-win32
#     ifdef __cplusplus
      extern "C" {
#     endif
         // Global APIs
         ErrorCode AdxDeviceGetLinkageInfo(
            int32   deviceParent,    /*IN*/
            int32   index,           /*IN*/
            int32   *deviceNumber,   /*OUT*/
            wchar_t *description,    /*OUT OPTIONAL*/
            int32   *subDeviceCount); /*OUT OPTIONAL*/

         ErrorCode AdxGetValueRangeInformation(
            ValueRange   type,         /*IN*/
            int32        descBufSize,  /*IN*/
            wchar_t      *description, /*OUT OPTIONAL*/
            MathInterval *range,       /*OUT OPTIONAL*/
            ValueUnit    *unit);        /*OUT OPTIONAL */

         ErrorCode AdxGetSignalConnectionInformation(
            SignalDrop     signal,      /*IN*/
            int32          descBufSize, /*IN*/
            wchar_t        *description,/*OUT OPTIONAL*/
            SignalPosition *position);   /*OUT OPTIONAL*/

         ErrorCode AdxEnumToString(
            wchar_t const *enumTypeName,    /*IN*/
            int32         enumValue,        /*IN*/
            int32         enumStringLength, /*IN*/
            wchar_t       *enumString);     /*OUT*/
         
         ErrorCode AdxStringToEnum(
            wchar_t const *enumTypeName,    /*IN*/
            wchar_t const *enumString,      /*IN*/
            int32         *enumValue);      /*OUT*/
         
         // Biodaq object create methods
         InstantAiCtrl* AdxInstantAiCtrlCreate();

         BufferedAiCtrl* AdxBufferedAiCtrlCreate();

         InstantAoCtrl* AdxInstantAoCtrlCreate();

         BufferedAoCtrl* AdxBufferedAoCtrlCreate();

         InstantDiCtrl* AdxInstantDiCtrlCreate();

         BufferedDiCtrl* AdxBufferedDiCtrlCreate();

         InstantDoCtrl* AdxInstantDoCtrlCreate();

         BufferedDoCtrl* AdxBufferedDoCtrlCreate();

         EventCounterCtrl* AdxEventCounterCtrlCreate();

         FreqMeterCtrl* AdxFreqMeterCtrlCreate();

         OneShotCtrl* AdxOneShotCtrlCreate();

         PwMeterCtrl* AdxPwMeterCtrlCreate();

         PwModulatorCtrl* AdxPwModulatorCtrlCreate();

         TimerPulseCtrl* AdxTimerPulseCtrlCreate();

         UdCounterCtrl* AdxUdCounterCtrlCreate();

#        if !defined(__cplusplus) || defined(_BDAQ_C_INTERFACE) // ANSI-C INTERFACE

         // ----------------------------------------------------------
         // common classes : ICollection (method index: 0~2)
         // ----------------------------------------------------------
         void  ICollection_Dispose(ICollection *_this);
         int32 ICollection_getCount(ICollection *_this);
         void* ICollection_getItem(ICollection *_this, int32 index);

         // ----------------------------------------------------------
         // common classes : AnalogChannel (method index: 3~5)
         // ----------------------------------------------------------
         int32      AnalogChannel_getChannel(AnalogChannel *_this);
         ValueRange AnalogChannel_getValueRange(AnalogChannel *_this);
         ErrorCode  AnalogChannel_setValueRange(AnalogChannel *_this, ValueRange value);

         // ----------------------------------------------------------
         // common classes : AnalogInputChannel (method index: 6~14)
         // ----------------------------------------------------------
         int32          AnalogInputChannel_getChannel(AnalogInputChannel *_this);
         ValueRange     AnalogInputChannel_getValueRange(AnalogInputChannel *_this);
         ErrorCode      AnalogInputChannel_setValueRange(AnalogInputChannel *_this, ValueRange value);
         AiSignalType   AnalogInputChannel_getSignalType(AnalogInputChannel *_this);
         ErrorCode      AnalogInputChannel_setSignalType(AnalogInputChannel *_this, AiSignalType value);
         BurnoutRetType AnalogInputChannel_getBurnoutRetType(AnalogInputChannel *_this);
         ErrorCode      AnalogInputChannel_setBurnoutRetType(AnalogInputChannel *_this, BurnoutRetType value);
         double         AnalogInputChannel_getBurnoutRetValue(AnalogInputChannel *_this);
         ErrorCode      AnalogInputChannel_setBurnoutRetValue(AnalogInputChannel *_this, double value);
         //New: Coupling & IEPE
         CouplingType   AnalogInputChannel_getCouplingType(AnalogInputChannel *_this);
         ErrorCode      AnalogInputChannel_setCouplingType(AnalogInputChannel *_this, CouplingType value);
         IepeType       AnalogInputChannel_getIepeType(AnalogInputChannel *_this);
         ErrorCode      AnalogInputChannel_setIepeType(AnalogInputChannel *_this, IepeType value);

         // ----------------------------------------------------------
         // common classes : CjcSetting (method index: 15~18)
         // ----------------------------------------------------------
         int32      CjcSetting_getChannel(CjcSetting *_this);
         ErrorCode  CjcSetting_setChannel(CjcSetting *_this, int32 ch);
         double     CjcSetting_getValue(CjcSetting *_this);
         ErrorCode  CjcSetting_setValue(CjcSetting *_this, double value);

         // ----------------------------------------------------------
         // common classes : ScanChannel (method index: 19~26)
         // ----------------------------------------------------------
         int32      ScanChannel_getChannelStart(ScanChannel *_this);
         ErrorCode  ScanChannel_setChannelStart(ScanChannel *_this, int32 value);
         int32      ScanChannel_getChannelCount(ScanChannel *_this);
         ErrorCode  ScanChannel_setChannelCount(ScanChannel *_this, int32 value);
         int32      ScanChannel_getSamples(ScanChannel *_this);
         ErrorCode  ScanChannel_setSamples(ScanChannel *_this, int32 value);
         int32      ScanChannel_getIntervalCount(ScanChannel *_this);
         ErrorCode  ScanChannel_setIntervalCount(ScanChannel *_this, int32 value);

         // ----------------------------------------------------------
         // common classes : ConvertClock (method index: 27~30)
         // ----------------------------------------------------------
         SignalDrop ConvertClock_getSource(ConvertClock *_this);
         ErrorCode  ConvertClock_setSource(ConvertClock *_this, SignalDrop value);
         double     ConvertClock_getRate(ConvertClock *_this);
         ErrorCode  ConvertClock_setRate(ConvertClock *_this, double value);

         // ----------------------------------------------------------
         // common classes : ScanClock (method index: 31~36)
         // ----------------------------------------------------------
         SignalDrop ScanClock_getSource(ScanClock *_this);
         ErrorCode  ScanClock_setSource(ScanClock *_this, SignalDrop value);
         double     ScanClock_getRate(ScanClock *_this);
         ErrorCode  ScanClock_setRate(ScanClock *_this, double value);
         int32      ScanClock_getScanCount(ScanClock *_this);
         ErrorCode  ScanClock_setScanCount(ScanClock *_this, int32 value);

         // ----------------------------------------------------------
         // common classes : Trigger (method index: 37~46)
         // ----------------------------------------------------------
         SignalDrop     Trigger_getSource(Trigger *_this);
         ErrorCode      Trigger_setSource(Trigger *_this,SignalDrop value);
         ActiveSignal   Trigger_getEdge(Trigger *_this);
         ErrorCode      Trigger_setEdge(Trigger *_this, ActiveSignal value);
         double         Trigger_getLevel(Trigger *_this);
         ErrorCode      Trigger_setLevel(Trigger *_this, double value);
         TriggerAction  Trigger_getAction(Trigger *_this);
         ErrorCode      Trigger_setAction(Trigger *_this, TriggerAction value);
         int32          Trigger_getDelayCount(Trigger *_this);
         ErrorCode      Trigger_setDelayCount(Trigger *_this, int32 value);

         // ----------------------------------------------------------
         // common classes : PortDirection (method index: 47~49)
         // ----------------------------------------------------------
         int32       PortDirection_getPort(PortDirection *_this);
         DioPortDir  PortDirection_getDirection(PortDirection *_this);
         ErrorCode   PortDirection_setDirection(PortDirection *_this, DioPortDir value);

         // ----------------------------------------------------------
         // common classes : NoiseFilterChannel (method index: 50~52)
         // ----------------------------------------------------------
         int32      NoiseFilterChannel_getChannel(NoiseFilterChannel *_this);
         int8       NoiseFilterChannel_getEnabled(NoiseFilterChannel *_this);
         ErrorCode  NoiseFilterChannel_setEnabled(NoiseFilterChannel *_this, int8 value);

         // ----------------------------------------------------------
         // common classes : DiintChannel (method index: 53~59)
         // ----------------------------------------------------------
         int32         DiintChannel_getChannel(DiintChannel *_this);
         int8          DiintChannel_getEnabled(DiintChannel *_this);
         ErrorCode     DiintChannel_setEnabled(DiintChannel *_this, int8 value);
         int8          DiintChannel_getGated(DiintChannel *_this);
         ErrorCode     DiintChannel_setGated(DiintChannel *_this, int8 value);
         ActiveSignal  DiintChannel_getTrigEdge(DiintChannel *_this);
         ErrorCode     DiintChannel_setTrigEdge(DiintChannel *_this, ActiveSignal value);

         // ----------------------------------------------------------
         // common classes : DiCosintPort (method index: 60~62)
         // ----------------------------------------------------------
         int32      DiCosintPort_getPort(DiCosintPort *_this);
         uint8      DiCosintPort_getMask(DiCosintPort *_this);
         ErrorCode  DiCosintPort_setMask(DiCosintPort *_this, uint8 value);

         // ----------------------------------------------------------
         // common classes : DiPmintPort (method index: 63~67)
         // ----------------------------------------------------------
         int32       DiPmintPort_getPort(DiPmintPort *_this);
         uint8       DiPmintPort_getMask(DiPmintPort *_this);
         ErrorCode   DiPmintPort_setMask(DiPmintPort *_this, uint8 value);
         uint8       DiPmintPort_getPattern(DiPmintPort *_this);
         ErrorCode   DiPmintPort_setPattern(DiPmintPort *_this, uint8 value);

         // ----------------------------------------------------------
         // common classes : ScanPort (method index: 68~75)
         // ----------------------------------------------------------
         int32      ScanPort_getPortStart(ScanPort *_this);
         ErrorCode  ScanPort_setPortStart(ScanPort *_this, int32 value);
         int32      ScanPort_getPortCount(ScanPort *_this);
         ErrorCode  ScanPort_setPortCount(ScanPort *_this, int32 value);
         int32      ScanPort_getSamples(ScanPort *_this);
         ErrorCode  ScanPort_setSamples(ScanPort *_this, int32 value);
         int32      ScanPort_getIntervalCount(ScanPort *_this);
         ErrorCode  ScanPort_setIntervalCount(ScanPort *_this, int32 value);

         // ----------------------------------------------------------
         // AI features (method index: 76~104)
         // ----------------------------------------------------------
         // ADC features
         int32  AiFeatures_getResolution(AiFeatures *_this);
         int32  AiFeatures_getDataSize(AiFeatures *_this);
         int32  AiFeatures_getDataMask(AiFeatures *_this);
         // channel features                                                        
         int32         AiFeatures_getChannelCountMax(AiFeatures *_this);
         AiChannelType AiFeatures_getChannelType(AiFeatures *_this);
         int8          AiFeatures_getOverallValueRange(AiFeatures *_this);
         int8          AiFeatures_getThermoSupported(AiFeatures *_this);
         ICollection*  AiFeatures_getValueRanges(AiFeatures *_this);
         ICollection*  AiFeatures_getBurnoutReturnTypes(AiFeatures *_this);
         // CJC features
         ICollection*  AiFeatures_getCjcChannels(AiFeatures *_this);
         // buffered ai->basic features
         int8           AiFeatures_getBufferedAiSupported(AiFeatures *_this);
         SamplingMethod AiFeatures_getSamplingMethod(AiFeatures *_this);
         int32          AiFeatures_getChannelStartBase(AiFeatures *_this);
         int32          AiFeatures_getChannelCountBase(AiFeatures *_this);
         // buffered ai->conversion clock features
         ICollection*  AiFeatures_getConvertClockSources(AiFeatures *_this);
         void          AiFeatures_getConvertClockRange(AiFeatures *_this, MathInterval *value);
         // buffered ai->burst scan
         int8          AiFeatures_getBurstScanSupported(AiFeatures *_this);
         ICollection*  AiFeatures_getScanClockSources(AiFeatures *_this);
         void          AiFeatures_getScanClockRange(AiFeatures *_this, MathInterval *value);
         int32         AiFeatures_getScanCountMax(AiFeatures *_this);
         // buffered ai->trigger features
         int8          AiFeatures_getTriggerSupported(AiFeatures *_this);
         int32         AiFeatures_getTriggerCount(AiFeatures *_this);
         ICollection*  AiFeatures_getTriggerSources(AiFeatures *_this);
         ICollection*  AiFeatures_getTriggerActions(AiFeatures *_this);
         void          AiFeatures_getTriggerDelayRange(AiFeatures *_this, MathInterval *value);
         // buffered ai->trigger1 features
         int8          AiFeatures_getTrigger1Supported(AiFeatures *_this);
         ICollection*  AiFeatures_getTrigger1Sources(AiFeatures *_this);
         ICollection*  AiFeatures_getTrigger1Actions(AiFeatures *_this);
         void          AiFeatures_getTrigger1DelayRange(AiFeatures *_this, MathInterval *value);

         // ----------------------------------------------------------
         // InstantAiCtrl (method index: 105~126)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       InstantAiCtrl_Dispose(InstantAiCtrl *_this);
         void       InstantAiCtrl_Cleanup(InstantAiCtrl *_this);
         ErrorCode  InstantAiCtrl_UpdateProperties(InstantAiCtrl *_this);
         void       InstantAiCtrl_addRemovedListener(InstantAiCtrl *_this, DeviceEventListener * listener);
         void       InstantAiCtrl_removeRemovedListener(InstantAiCtrl *_this, DeviceEventListener * listener);
         void       InstantAiCtrl_addReconnectedListener(InstantAiCtrl *_this, DeviceEventListener * listener);
         void       InstantAiCtrl_removeReconnectedListener(InstantAiCtrl *_this, DeviceEventListener * listener);
         void       InstantAiCtrl_addPropertyChangedListener(InstantAiCtrl *_this, DeviceEventListener * listener);
         void       InstantAiCtrl_removePropertyChangedListener(InstantAiCtrl *_this, DeviceEventListener * listener);
         void       InstantAiCtrl_getSelectedDevice(InstantAiCtrl *_this, DeviceInformation *x);
         ErrorCode  InstantAiCtrl_setSelectedDevice(InstantAiCtrl *_this, DeviceInformation const *x);
         int8       InstantAiCtrl_getInitialized(InstantAiCtrl *_this);
         int8       InstantAiCtrl_getCanEditProperty(InstantAiCtrl *_this);
         HANDLE     InstantAiCtrl_getDevice(InstantAiCtrl *_this);
         HANDLE     InstantAiCtrl_getModule(InstantAiCtrl *_this);
         ICollection* InstantAiCtrl_getSupportedDevices(InstantAiCtrl *_this);
         ICollection* InstantAiCtrl_getSupportedModes(InstantAiCtrl *_this);
         /* Methods derived from AiCtrlBase */
         AiFeatures*  InstantAiCtrl_getFeatures(InstantAiCtrl *_this);
         ICollection* InstantAiCtrl_getChannels(InstantAiCtrl *_this);
         int32        InstantAiCtrl_getChannelCount(InstantAiCtrl *_this);
         /* InstantAiCtrl methods */
         ErrorCode    InstantAiCtrl_ReadAny(InstantAiCtrl *_this, int32 chStart, int32 chCount, void *dataRaw, double *dataScaled);
         CjcSetting*  InstantAiCtrl_getCjc(InstantAiCtrl *_this);

         // ----------------------------------------------------------
         // BufferedAiCtrl (method index: 127~173)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       BufferedAiCtrl_Dispose(BufferedAiCtrl *_this);
         void       BufferedAiCtrl_Cleanup(BufferedAiCtrl *_this);
         ErrorCode  BufferedAiCtrl_UpdateProperties(BufferedAiCtrl *_this);
         void       BufferedAiCtrl_addRemovedListener(BufferedAiCtrl *_this, DeviceEventListener * listener);
         void       BufferedAiCtrl_removeRemovedListener(BufferedAiCtrl *_this, DeviceEventListener * listener);
         void       BufferedAiCtrl_addReconnectedListener(BufferedAiCtrl *_this, DeviceEventListener * listener);
         void       BufferedAiCtrl_removeReconnectedListener(BufferedAiCtrl *_this, DeviceEventListener * listener);
         void       BufferedAiCtrl_addPropertyChangedListener(BufferedAiCtrl *_this, DeviceEventListener * listener);
         void       BufferedAiCtrl_removePropertyChangedListener(BufferedAiCtrl *_this, DeviceEventListener * listener);
         void       BufferedAiCtrl_getSelectedDevice(BufferedAiCtrl *_this, DeviceInformation *x);
         ErrorCode  BufferedAiCtrl_setSelectedDevice(BufferedAiCtrl *_this, DeviceInformation const *x);
         int8       BufferedAiCtrl_getInitialized(BufferedAiCtrl *_this);
         int8       BufferedAiCtrl_getCanEditProperty(BufferedAiCtrl *_this);
         HANDLE     BufferedAiCtrl_getDevice(BufferedAiCtrl *_this);
         HANDLE     BufferedAiCtrl_getModule(BufferedAiCtrl *_this);
         ICollection*  BufferedAiCtrl_getSupportedDevices(BufferedAiCtrl *_this);
         ICollection*  BufferedAiCtrl_getSupportedModes(BufferedAiCtrl *_this);
         /* Methods derived from AiCtrlBase */                                                                                  
         AiFeatures*   BufferedAiCtrl_getFeatures(BufferedAiCtrl *_this);
         ICollection*  BufferedAiCtrl_getChannels(BufferedAiCtrl *_this);
         int32         BufferedAiCtrl_getChannelCount(BufferedAiCtrl *_this);
         /* BufferedAiCtrl methods */
         // event
         void       BufferedAiCtrl_addDataReadyListener(BufferedAiCtrl *_this, BfdAiEventListener *listener);
         void       BufferedAiCtrl_removeDataReadyListener(BufferedAiCtrl *_this, BfdAiEventListener *listener);
         void       BufferedAiCtrl_addOverrunListener(BufferedAiCtrl *_this, BfdAiEventListener *listener);
         void       BufferedAiCtrl_removeOverrunListener(BufferedAiCtrl *_this, BfdAiEventListener *listener);
         void       BufferedAiCtrl_addCacheOverflowListener(BufferedAiCtrl *_this, BfdAiEventListener *listener);
         void       BufferedAiCtrl_removeCacheOverflowListener(BufferedAiCtrl *_this, BfdAiEventListener *listener);
         void       BufferedAiCtrl_addStoppedListener(BufferedAiCtrl *_this, BfdAiEventListener *listener);
         void       BufferedAiCtrl_removeStoppedListener(BufferedAiCtrl *_this, BfdAiEventListener *listener);
         // method
         ErrorCode  BufferedAiCtrl_Prepare(BufferedAiCtrl *_this);
         ErrorCode  BufferedAiCtrl_RunOnce(BufferedAiCtrl *_this);
         ErrorCode  BufferedAiCtrl_Start(BufferedAiCtrl *_this);
         ErrorCode  BufferedAiCtrl_Stop(BufferedAiCtrl *_this);
         ErrorCode  BufferedAiCtrl_GetDataI16(BufferedAiCtrl *_this, int32 count, int16 rawData[]);
         ErrorCode  BufferedAiCtrl_GetDataI32(BufferedAiCtrl *_this, int32 count, int32 rawData[]);
         ErrorCode  BufferedAiCtrl_GetDataF64(BufferedAiCtrl *_this, int32 count, double scaledData[]);
         void       BufferedAiCtrl_Release(BufferedAiCtrl *_this);
         // property
         void*         BufferedAiCtrl_getBuffer(BufferedAiCtrl *_this);
         int32         BufferedAiCtrl_getBufferCapacity(BufferedAiCtrl *_this);
         ControlState  BufferedAiCtrl_getState(BufferedAiCtrl *_this);
         ScanChannel*  BufferedAiCtrl_getScanChannel(BufferedAiCtrl *_this);
         ConvertClock* BufferedAiCtrl_getConvertClock(BufferedAiCtrl *_this);
         ScanClock*    BufferedAiCtrl_getScanClock(BufferedAiCtrl *_this);
         Trigger*      BufferedAiCtrl_getTrigger(BufferedAiCtrl *_this);
         int8          BufferedAiCtrl_getStreaming(BufferedAiCtrl *_this);
         ErrorCode     BufferedAiCtrl_setStreaming(BufferedAiCtrl *_this, int8 value);
         // method
         ErrorCode     BufferedAiCtrl_GetEventStatus(BufferedAiCtrl *_this, EventId id, int32 *status);
         // property
         Trigger*      BufferedAiCtrl_getTrigger1(BufferedAiCtrl *_this);

         // ----------------------------------------------------------
         // AO features (method index: 174~195)
         // ----------------------------------------------------------
         // DAC features                                                               
         int32  AoFeatures_getResolution(AoFeatures *_this);
         int32  AoFeatures_getDataSize(AoFeatures *_this);
         int32  AoFeatures_getDataMask(AoFeatures *_this);
         // channel features                                                                               
         int32        AoFeatures_getChannelCountMax(AoFeatures *_this);
         ICollection* AoFeatures_getValueRanges(AoFeatures *_this);
         int8         AoFeatures_getExternalRefAntiPolar(AoFeatures *_this);
         void         AoFeatures_getExternalRefRange(AoFeatures *_this, MathInterval *value);
         // buffered ao->basic features                                                
         int8           AoFeatures_getBufferedAoSupported(AoFeatures *_this);
         SamplingMethod AoFeatures_getSamplingMethod(AoFeatures *_this);
         int32          AoFeatures_getChannelStartBase(AoFeatures *_this);
         int32          AoFeatures_getChannelCountBase(AoFeatures *_this);
         // buffered ao->conversion clock features                                                       
         ICollection*   AoFeatures_getConvertClockSources(AoFeatures *_this);
         void           AoFeatures_getConvertClockRange(AoFeatures *_this, MathInterval *value);
         // buffered ao->trigger features                                              
         int8           AoFeatures_getTriggerSupported(AoFeatures *_this);
         int32          AoFeatures_getTriggerCount(AoFeatures *_this);
         ICollection*   AoFeatures_getTriggerSources(AoFeatures *_this);
         ICollection*   AoFeatures_getTriggerActions(AoFeatures *_this);
         void           AoFeatures_getTriggerDelayRange(AoFeatures *_this, MathInterval *value);
         // buffered ao->trigger1 features                                                               
         int8           AoFeatures_getTrigger1Supported(AoFeatures *_this);
         ICollection*   AoFeatures_getTrigger1Sources(AoFeatures *_this);
         ICollection*   AoFeatures_getTrigger1Actions(AoFeatures *_this);
         MathInterval   AoFeatures_getTrigger1DelayRange(AoFeatures *_this);

         // ----------------------------------------------------------
         // InstantAoCtrl (method index: 196~220)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       InstantAoCtrl_Dispose(InstantAoCtrl *_this);
         void       InstantAoCtrl_Cleanup(InstantAoCtrl *_this);
         ErrorCode  InstantAoCtrl_UpdateProperties(InstantAoCtrl *_this);
         void       InstantAoCtrl_addRemovedListener(InstantAoCtrl *_this, DeviceEventListener * listener);
         void       InstantAoCtrl_removeRemovedListener(InstantAoCtrl *_this, DeviceEventListener * listener);
         void       InstantAoCtrl_addReconnectedListener(InstantAoCtrl *_this, DeviceEventListener * listener);
         void       InstantAoCtrl_removeReconnectedListener(InstantAoCtrl *_this, DeviceEventListener * listener);
         void       InstantAoCtrl_addPropertyChangedListener(InstantAoCtrl *_this, DeviceEventListener * listener);
         void       InstantAoCtrl_removePropertyChangedListener(InstantAoCtrl *_this, DeviceEventListener * listener);
         void       InstantAoCtrl_getSelectedDevice(InstantAoCtrl *_this, DeviceInformation *x);
         ErrorCode  InstantAoCtrl_setSelectedDevice(InstantAoCtrl *_this, DeviceInformation const *x);
         int8       InstantAoCtrl_getInitialized(InstantAoCtrl *_this);
         int8       InstantAoCtrl_getCanEditProperty(InstantAoCtrl *_this);
         HANDLE     InstantAoCtrl_getDevice(InstantAoCtrl *_this);
         HANDLE     InstantAoCtrl_getModule(InstantAoCtrl *_this);
         ICollection* InstantAoCtrl_getSupportedDevices(InstantAoCtrl *_this);
         ICollection* InstantAoCtrl_getSupportedModes(InstantAoCtrl *_this);
         /* Methods derived from AiCtrlBase */                                                                                 
         AoFeatures*  InstantAoCtrl_getFeatures(InstantAoCtrl *_this);
         ICollection* InstantAoCtrl_getChannels(InstantAoCtrl *_this);
         int32        InstantAoCtrl_getChannelCount(InstantAoCtrl *_this);
         double       InstantAoCtrl_getExtRefValueForUnipolar(InstantAoCtrl *_this);
         ErrorCode    InstantAoCtrl_setExtRefValueForUnipolar(InstantAoCtrl *_this, double value);
         double       InstantAoCtrl_getExtRefValueForBipolar(InstantAoCtrl *_this);
         ErrorCode    InstantAoCtrl_setExtRefValueForBipolar(InstantAoCtrl *_this, double value);
         /* InstantAoCtrl methods */
         ErrorCode    InstantAoCtrl_WriteAny(InstantAoCtrl *_this, int32 chStart, int32 chCount, void *dataRaw, double *dataScaled);

         // ----------------------------------------------------------
         // BufferedAoCtrl (method index: 221~271)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       BufferedAoCtrl_Dispose(BufferedAoCtrl *_this);
         void       BufferedAoCtrl_Cleanup(BufferedAoCtrl *_this);
         ErrorCode  BufferedAoCtrl_UpdateProperties(BufferedAoCtrl *_this);
         void       BufferedAoCtrl_addRemovedListener(BufferedAoCtrl *_this, DeviceEventListener * listener);
         void       BufferedAoCtrl_removeRemovedListener(BufferedAoCtrl *_this, DeviceEventListener * listener);
         void       BufferedAoCtrl_addReconnectedListener(BufferedAoCtrl *_this, DeviceEventListener * listener);
         void       BufferedAoCtrl_removeReconnectedListener(BufferedAoCtrl *_this, DeviceEventListener * listener);
         void       BufferedAoCtrl_addPropertyChangedListener(BufferedAoCtrl *_this, DeviceEventListener * listener);
         void       BufferedAoCtrl_removePropertyChangedListener(BufferedAoCtrl *_this, DeviceEventListener * listener);
         void       BufferedAoCtrl_getSelectedDevice(BufferedAoCtrl *_this, DeviceInformation *x);
         ErrorCode  BufferedAoCtrl_setSelectedDevice(BufferedAoCtrl *_this, DeviceInformation const *x);
         int8       BufferedAoCtrl_getInitialized(BufferedAoCtrl *_this);
         int8       BufferedAoCtrl_getCanEditProperty(BufferedAoCtrl *_this);
         HANDLE     BufferedAoCtrl_getDevice(BufferedAoCtrl *_this);
         HANDLE     BufferedAoCtrl_getModule(BufferedAoCtrl *_this);
         ICollection*  BufferedAoCtrl_getSupportedDevices(BufferedAoCtrl *_this);
         ICollection*  BufferedAoCtrl_getSupportedModes(BufferedAoCtrl *_this);
         /* Methods derived from AiCtrlBase */                                                                                  
         AoFeatures*   BufferedAoCtrl_getFeatures(BufferedAoCtrl *_this);
         ICollection*  BufferedAoCtrl_getChannels(BufferedAoCtrl *_this);
         int32         BufferedAoCtrl_getChannelCount(BufferedAoCtrl *_this);
         double        BufferedAoCtrl_getExtRefValueForUnipolar(InstantAoCtrl *_this);
         ErrorCode     BufferedAoCtrl_setExtRefValueForUnipolar(InstantAoCtrl *_this, double value);
         double        BufferedAoCtrl_getExtRefValueForBipolar(InstantAoCtrl *_this);
         ErrorCode     BufferedAoCtrl_setExtRefValueForBipolar(InstantAoCtrl *_this, double value);
         /* BufferedAoCtrl methods */
         // event
         void       BufferedAoCtrl_addDataTransmittedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener);
         void       BufferedAoCtrl_removeDataTransmittedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener);
         void       BufferedAoCtrl_addUnderrunListener(BufferedAoCtrl *_this, BfdAoEventListener *listener);
         void       BufferedAoCtrl_removeUnderrunListener(BufferedAoCtrl *_this, BfdAoEventListener *listener);
         void       BufferedAoCtrl_addCacheEmptiedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener);
         void       BufferedAoCtrl_removeCacheEmptiedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener);
         void       BufferedAoCtrl_addTransitStoppedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener);
         void       BufferedAoCtrl_removeTransitStoppedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener);
         void       BufferedAoCtrl_addStoppedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener);
         void       BufferedAoCtrl_removeStoppedListener(BufferedAoCtrl *_this, BfdAoEventListener *listener);
         // method
         ErrorCode  BufferedAoCtrl_Prepare(BufferedAoCtrl *_this);
         ErrorCode  BufferedAoCtrl_RunOnce(BufferedAoCtrl *_this);
         ErrorCode  BufferedAoCtrl_Start(BufferedAoCtrl *_this);
         ErrorCode  BufferedAoCtrl_Stop(BufferedAoCtrl *_this, int32 action);
         ErrorCode  BufferedAoCtrl_SetDataI16(BufferedAoCtrl *_this, int32 count, int16 rawData[]);
         ErrorCode  BufferedAoCtrl_SetDataI32(BufferedAoCtrl *_this, int32 count, int32 rawData[]);
         ErrorCode  BufferedAoCtrl_SetDataF64(BufferedAoCtrl *_this, int32 count, double scaledData[]);
         void       BufferedAoCtrl_Release(BufferedAoCtrl *_this);
         // property
         void*         BufferedAoCtrl_getBuffer(BufferedAoCtrl *_this);
         int32         BufferedAoCtrl_getBufferCapacity(BufferedAoCtrl *_this);
         ControlState  BufferedAoCtrl_getState(BufferedAoCtrl *_this);
         ScanChannel*  BufferedAoCtrl_getScanChannel(BufferedAoCtrl *_this);
         ConvertClock* BufferedAoCtrl_getConvertClock(BufferedAoCtrl *_this);
         Trigger*      BufferedAoCtrl_getTrigger(BufferedAoCtrl *_this);
         int8          BufferedAoCtrl_getStreaming(BufferedAoCtrl *_this);
         ErrorCode     BufferedAoCtrl_setStreaming(BufferedAoCtrl *_this, int8 value);
         Trigger*      BufferedAoCtrl_getTrigger1(BufferedAoCtrl *_this);

         // ----------------------------------------------------------
         // DI features (method index: 272~304)
         // ----------------------------------------------------------
         int8          DiFeatures_getPortProgrammable(DiFeatures *_this);
         int32         DiFeatures_getPortCount(DiFeatures *_this);
         ICollection*  DiFeatures_getPortsType(DiFeatures *_this);
         int8          DiFeatures_getDiSupported(DiFeatures *_this);
         int8          DiFeatures_getDoSupported(DiFeatures *_this);
         int32         DiFeatures_getChannelCountMax(DiFeatures *_this);
         ICollection*  DiFeatures_getDataMask(DiFeatures *_this);
         // di noise filter features                                                                                      
         int8          DiFeatures_getNoiseFilterSupported(DiFeatures *_this);
         ICollection*  DiFeatures_getNoiseFilterOfChannels(DiFeatures *_this);
         void          DiFeatures_getNoiseFilterBlockTimeRange(DiFeatures *_this, MathInterval *value);
         // di interrupt features                                                               
         int8          DiFeatures_getDiintSupported(DiFeatures *_this);
         int8          DiFeatures_getDiintGateSupported(DiFeatures *_this);
         int8          DiFeatures_getDiCosintSupported(DiFeatures *_this);
         int8          DiFeatures_getDiPmintSupported(DiFeatures *_this);
         ICollection*  DiFeatures_getDiintTriggerEdges(DiFeatures *_this);
         ICollection*  DiFeatures_getDiintOfChannels(DiFeatures *_this);
         ICollection*  DiFeatures_getDiintGateOfChannels(DiFeatures *_this);
         ICollection*  DiFeatures_getDiCosintOfPorts(DiFeatures *_this);
         ICollection*  DiFeatures_getDiPmintOfPorts(DiFeatures *_this);
         ICollection*  DiFeatures_getSnapEventSources(DiFeatures *_this);
         // buffered di->basic features                                                         
         int8           DiFeatures_getBufferedDiSupported(DiFeatures *_this);
         SamplingMethod DiFeatures_getSamplingMethod(DiFeatures *_this);
         // buffered di->conversion clock features                                              
         ICollection*  DiFeatures_getConvertClockSources(DiFeatures *_this);
         void          DiFeatures_getConvertClockRange(DiFeatures *_this, MathInterval *value);
         // buffered di->burst scan                                                             
         int8          DiFeatures_getBurstScanSupported(DiFeatures *_this);
         ICollection*  DiFeatures_getScanClockSources(DiFeatures *_this);
         void          DiFeatures_getScanClockRange(DiFeatures *_this, MathInterval *value);
         int32         DiFeatures_getScanCountMax(DiFeatures *_this);
         // buffered di->trigger features                                                       
         int8          DiFeatures_getTriggerSupported(DiFeatures *_this);
         int32         DiFeatures_getTriggerCount(DiFeatures *_this);
         ICollection*  DiFeatures_getTriggerSources(DiFeatures *_this);
         ICollection*  DiFeatures_getTriggerActions(DiFeatures *_this);
         void          DiFeatures_getTriggerDelayRange(DiFeatures *_this, MathInterval *value);

         // ----------------------------------------------------------
         // InstantDiCtrl (method index: 305~337)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       InstantDiCtrl_Dispose(InstantDiCtrl *_this);
         void       InstantDiCtrl_Cleanup(InstantDiCtrl *_this);
         ErrorCode  InstantDiCtrl_UpdateProperties(InstantDiCtrl *_this);
         void       InstantDiCtrl_addRemovedListener(InstantDiCtrl *_this, DeviceEventListener * listener);
         void       InstantDiCtrl_removeRemovedListener(InstantDiCtrl *_this, DeviceEventListener * listener);
         void       InstantDiCtrl_addReconnectedListener(InstantDiCtrl *_this, DeviceEventListener * listener);
         void       InstantDiCtrl_removeReconnectedListener(InstantDiCtrl *_this, DeviceEventListener * listener);
         void       InstantDiCtrl_addPropertyChangedListener(InstantDiCtrl *_this, DeviceEventListener * listener);
         void       InstantDiCtrl_removePropertyChangedListener(InstantDiCtrl *_this, DeviceEventListener * listener);
         void       InstantDiCtrl_getSelectedDevice(InstantDiCtrl *_this, DeviceInformation *x);
         ErrorCode  InstantDiCtrl_setSelectedDevice(InstantDiCtrl *_this, DeviceInformation const *x);
         int8       InstantDiCtrl_getInitialized(InstantDiCtrl *_this);
         int8       InstantDiCtrl_getCanEditProperty(InstantDiCtrl *_this);
         HANDLE     InstantDiCtrl_getDevice(InstantDiCtrl *_this);
         HANDLE     InstantDiCtrl_getModule(InstantDiCtrl *_this);
         ICollection* InstantDiCtrl_getSupportedDevices(InstantDiCtrl *_this);
         ICollection* InstantDiCtrl_getSupportedModes(InstantDiCtrl *_this);
         /* Methods derived from DioCtrlBase */
         int32        InstantDiCtrl_getPortCount(InstantDiCtrl *_this);
         ICollection* InstantDiCtrl_getPortDirection(InstantDiCtrl *_this);
         /* Methods derived from DiCtrlBase */ 
         DiFeatures*  InstantDiCtrl_getFeatures(InstantDiCtrl *_this);
         ICollection* InstantDiCtrl_getNoiseFilter(InstantDiCtrl *_this);
         /* Instant DI methods */
         // event
         void         InstantDiCtrl_addInterruptListener(InstantDiCtrl *_this, DiSnapEventListener * listener);
         void         InstantDiCtrl_removeInterruptListener(InstantDiCtrl *_this, DiSnapEventListener * listener);
         void         InstantDiCtrl_addChangeOfStateListener(InstantDiCtrl *_this, DiSnapEventListener * listener);
         void         InstantDiCtrl_removeChangeOfStateListener(InstantDiCtrl *_this, DiSnapEventListener * listener);
         void         InstantDiCtrl_addPatternMatchListener(InstantDiCtrl *_this, DiSnapEventListener * listener);
         void         InstantDiCtrl_removePatternMatchListener(InstantDiCtrl *_this, DiSnapEventListener * listener);
         // method                                                                                                            
         ErrorCode    InstantDiCtrl_ReadAny(InstantDiCtrl *_this, int32 portStart, int32 portCount, uint8 data[]);
         ErrorCode    InstantDiCtrl_ReadBit(InstantDiCtrl *_this, int32 port, int32 bit, uint8* data);
         ErrorCode    InstantDiCtrl_SnapStart(InstantDiCtrl *_this);
         ErrorCode    InstantDiCtrl_SnapStop(InstantDiCtrl *_this);
         // property                                                                                                          
         ICollection* InstantDiCtrl_getDiintChannels(InstantDiCtrl *_this);
         ICollection* InstantDiCtrl_getDiCosintPorts(InstantDiCtrl *_this);
         ICollection* InstantDiCtrl_getDiPmintPorts(InstantDiCtrl *_this);

         // ----------------------------------------------------------
         // BufferedDiCtrl (method index: 338~381)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       BufferedDiCtrl_Dispose(BufferedDiCtrl *_this);
         void       BufferedDiCtrl_Cleanup(BufferedDiCtrl *_this);
         ErrorCode  BufferedDiCtrl_UpdateProperties(BufferedDiCtrl *_this);
         void       BufferedDiCtrl_addRemovedListener(BufferedDiCtrl *_this, DeviceEventListener * listener);
         void       BufferedDiCtrl_removeRemovedListener(BufferedDiCtrl *_this, DeviceEventListener * listener);
         void       BufferedDiCtrl_addReconnectedListener(BufferedDiCtrl *_this, DeviceEventListener * listener);
         void       BufferedDiCtrl_removeReconnectedListener(BufferedDiCtrl *_this, DeviceEventListener * listener);
         void       BufferedDiCtrl_addPropertyChangedListener(BufferedDiCtrl *_this, DeviceEventListener * listener);
         void       BufferedDiCtrl_removePropertyChangedListener(BufferedDiCtrl *_this, DeviceEventListener * listener);
         void       BufferedDiCtrl_getSelectedDevice(BufferedDiCtrl *_this, DeviceInformation *x);
         ErrorCode  BufferedDiCtrl_setSelectedDevice(BufferedDiCtrl *_this, DeviceInformation const *x);
         int8       BufferedDiCtrl_getInitialized(BufferedDiCtrl *_this);
         int8       BufferedDiCtrl_getCanEditProperty(BufferedDiCtrl *_this);
         HANDLE     BufferedDiCtrl_getDevice(BufferedDiCtrl *_this);
         HANDLE     BufferedDiCtrl_getModule(BufferedDiCtrl *_this);
         ICollection*  BufferedDiCtrl_getSupportedDevices(BufferedDiCtrl *_this);
         ICollection*  BufferedDiCtrl_getSupportedModes(BufferedDiCtrl *_this);
         /* Methods derived from DioCtrlBase */                                                                                 
         int32         BufferedDiCtrl_getPortCount(BufferedDiCtrl *_this);
         ICollection*  BufferedDiCtrl_getPortDirection(BufferedDiCtrl *_this);
         /* Methods derived from DiCtrlBase */                                                                                  
         DiFeatures*   BufferedDiCtrl_getFeatures(BufferedDiCtrl *_this);
         ICollection*  BufferedDiCtrl_getNoiseFilter(BufferedDiCtrl *_this);
         /* Buffered DI methods */
         // event
         void          BufferedDiCtrl_addDataReadyListener(BufferedDiCtrl *_this, BfdDiEventListener *listener);
         void          BufferedDiCtrl_removeDataReadyListener(BufferedDiCtrl *_this, BfdDiEventListener *listener);
         void          BufferedDiCtrl_addOverrunListener(BufferedDiCtrl *_this, BfdDiEventListener *listener);
         void          BufferedDiCtrl_removeOverrunListener(BufferedDiCtrl *_this, BfdDiEventListener *listener);
         void          BufferedDiCtrl_addCacheOverflowListener(BufferedDiCtrl *_this, BfdDiEventListener *listener);
         void          BufferedDiCtrl_removeCacheOverflowListener(BufferedDiCtrl *_this, BfdDiEventListener *listener);
         void          BufferedDiCtrl_addStoppedListener(BufferedDiCtrl *_this, BfdDiEventListener *listener);
         void          BufferedDiCtrl_removeStoppedListener(BufferedDiCtrl *_this, BfdDiEventListener *listener);
         // method
         ErrorCode     BufferedDiCtrl_Prepare(BufferedDiCtrl *_this);
         ErrorCode     BufferedDiCtrl_RunOnce(BufferedDiCtrl *_this);
         ErrorCode     BufferedDiCtrl_Start(BufferedDiCtrl *_this);
         ErrorCode     BufferedDiCtrl_Stop(BufferedDiCtrl *_this);
         ErrorCode     BufferedDiCtrl_GetData(BufferedDiCtrl *_this, int32 count, uint8 data[]);
         void          BufferedDiCtrl_Release(BufferedDiCtrl *_this);
         // property
         void*         BufferedDiCtrl_getBuffer(BufferedDiCtrl *_this);
         int32         BufferedDiCtrl_getBufferCapacity(BufferedDiCtrl *_this);
         ControlState  BufferedDiCtrl_getState(BufferedDiCtrl *_this);
         ScanPort*     BufferedDiCtrl_getScanPort(BufferedDiCtrl *_this);
         ConvertClock* BufferedDiCtrl_getConvertClock(BufferedDiCtrl *_this);
         ScanClock*    BufferedDiCtrl_getScanClock(BufferedDiCtrl *_this);
         Trigger*      BufferedDiCtrl_getTrigger(BufferedDiCtrl *_this);
         int8          BufferedDiCtrl_getStreaming(BufferedDiCtrl *_this);
         ErrorCode     BufferedDiCtrl_setStreaming(BufferedDiCtrl *_this, int8 value);

         // ----------------------------------------------------------
         // DO features (method index: 382~403)
         // ----------------------------------------------------------
         int8           DoFeatures_getPortProgrammable(DoFeatures *_this);
         int32          DoFeatures_getPortCount(DoFeatures *_this);
         ICollection*   DoFeatures_getPortsType(DoFeatures *_this);
         int8           DoFeatures_getDiSupported(DoFeatures *_this);
         int8           DoFeatures_getDoSupported(DoFeatures *_this);
         int32          DoFeatures_getChannelCountMax(DoFeatures *_this);
         ICollection*   DoFeatures_getDataMask(DoFeatures *_this);
         // do freeze features                                                                                       
         ICollection*   DoFeatures_getDoFreezeSignalSources(DoFeatures *_this);
         // do reflect Wdt features                                                             
         void           DoFeatures_getDoReflectWdtFeedIntervalRange(DoFeatures *_this, MathInterval *value);
         // buffered do->basic features                                                         
         int8           DoFeatures_getBufferedDoSupported(DoFeatures *_this);
         SamplingMethod DoFeatures_getSamplingMethod(DoFeatures *_this);
         // buffered do->conversion clock features                                              
         ICollection*   DoFeatures_getConvertClockSources(DoFeatures *_this);
         void           DoFeatures_getConvertClockRange(DoFeatures *_this, MathInterval *value);
         // buffered do->burst scan                                                             
         int8           DoFeatures_getBurstScanSupported(DoFeatures *_this);
         ICollection*   DoFeatures_getScanClockSources(DoFeatures *_this);
         void           DoFeatures_getScanClockRange(DoFeatures *_this, MathInterval *value);
         int32          DoFeatures_getScanCountMax(DoFeatures *_this);
         // buffered do->trigger features                                                                            
         int8           DoFeatures_getTriggerSupported(DoFeatures *_this);
         int32          DoFeatures_getTriggerCount(DoFeatures *_this);
         ICollection*   DoFeatures_getTriggerSources(DoFeatures *_this);
         ICollection*   DoFeatures_getTriggerActions(DoFeatures *_this);
         void           DoFeatures_getTriggerDelayRange(DoFeatures *_this, MathInterval *value);

         // ----------------------------------------------------------
         // InstantDoCtrl (method index: 404~425)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       InstantDoCtrl_Dispose(InstantDoCtrl *_this);
         void       InstantDoCtrl_Cleanup(InstantDoCtrl *_this);
         ErrorCode  InstantDoCtrl_UpdateProperties(InstantDoCtrl *_this);
         void       InstantDoCtrl_addRemovedListener(InstantDoCtrl *_this, DeviceEventListener * listener);
         void       InstantDoCtrl_removeRemovedListener(InstantDoCtrl *_this, DeviceEventListener * listener);
         void       InstantDoCtrl_addReconnectedListener(InstantDoCtrl *_this, DeviceEventListener * listener);
         void       InstantDoCtrl_removeReconnectedListener(InstantDoCtrl *_this, DeviceEventListener * listener);
         void       InstantDoCtrl_addPropertyChangedListener(InstantDoCtrl *_this, DeviceEventListener * listener);
         void       InstantDoCtrl_removePropertyChangedListener(InstantDoCtrl *_this, DeviceEventListener * listener);
         void       InstantDoCtrl_getSelectedDevice(InstantDoCtrl *_this, DeviceInformation *x);
         ErrorCode  InstantDoCtrl_setSelectedDevice(InstantDoCtrl *_this, DeviceInformation const *x);
         int8       InstantDoCtrl_getInitialized(InstantDoCtrl *_this);
         int8       InstantDoCtrl_getCanEditProperty(InstantDoCtrl *_this);
         HANDLE     InstantDoCtrl_getDevice(InstantDoCtrl *_this);
         HANDLE     InstantDoCtrl_getModule(InstantDoCtrl *_this);
         ICollection* InstantDoCtrl_getSupportedDevices(InstantDoCtrl *_this);
         ICollection* InstantDoCtrl_getSupportedModes(InstantDoCtrl *_this);
         /* Methods derived from DioCtrlBase */
         int32        InstantDoCtrl_getPortCount(InstantDoCtrl *_this);
         ICollection* InstantDoCtrl_getPortDirection(InstantDoCtrl *_this);
         /* Methods derived from DoCtrlBase */ 
         DoFeatures*  InstantDoCtrl_getFeatures(InstantDoCtrl *_this);
         /* Instant DO methods */
         ErrorCode    InstantDoCtrl_WriteAny(InstantDoCtrl *_this, int32 portStart, int32 portCount, uint8 data[]);
         ErrorCode    InstantDoCtrl_ReadAny(InstantDoCtrl *_this, int32 portStart, int32 portCount, uint8 data[]);
         ErrorCode    InstantDoCtrl_WriteBit(InstantDoCtrl *_this, int32 port, int32 bit, uint8 data);
         ErrorCode    InstantDoCtrl_ReadBit(InstantDoCtrl *_this, int32 port, int32 bit, uint8* data);

         // ----------------------------------------------------------
         // BufferedDoCtrl (method index: 426~469)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       BufferedDoCtrl_Dispose(BufferedDoCtrl *_this);
         void       BufferedDoCtrl_Cleanup(BufferedDoCtrl *_this);
         ErrorCode  BufferedDoCtrl_UpdateProperties(BufferedDoCtrl *_this);
         void       BufferedDoCtrl_addRemovedListener(BufferedDoCtrl *_this, DeviceEventListener * listener);
         void       BufferedDoCtrl_removeRemovedListener(BufferedDoCtrl *_this, DeviceEventListener * listener);
         void       BufferedDoCtrl_addReconnectedListener(BufferedDoCtrl *_this, DeviceEventListener * listener);
         void       BufferedDoCtrl_removeReconnectedListener(BufferedDoCtrl *_this, DeviceEventListener * listener);
         void       BufferedDoCtrl_addPropertyChangedListener(BufferedDoCtrl *_this, DeviceEventListener * listener);
         void       BufferedDoCtrl_removePropertyChangedListener(BufferedDoCtrl *_this, DeviceEventListener * listener);
         void       BufferedDoCtrl_getSelectedDevice(BufferedDoCtrl *_this, DeviceInformation *x);
         ErrorCode  BufferedDoCtrl_setSelectedDevice(BufferedDoCtrl *_this, DeviceInformation const *x);
         int8       BufferedDoCtrl_getInitialized(BufferedDoCtrl *_this);
         int8       BufferedDoCtrl_getCanEditProperty(BufferedDoCtrl *_this);
         HANDLE     BufferedDoCtrl_getDevice(BufferedDoCtrl *_this);
         HANDLE     BufferedDoCtrl_getModule(BufferedDoCtrl *_this);
         ICollection*  BufferedDoCtrl_getSupportedDevices(BufferedDoCtrl *_this);
         ICollection*  BufferedDoCtrl_getSupportedModes(BufferedDoCtrl *_this);
         /* Methods derived from DioCtrlBase */                                                                                   
         int32         BufferedDoCtrl_getPortCount(BufferedDoCtrl *_this);
         ICollection*  BufferedDoCtrl_getPortDirection(BufferedDoCtrl *_this);
         /* Methods derived from DoCtrlBase */                                                                                  
         DoFeatures*   BufferedDoCtrl_getFeatures(BufferedDoCtrl *_this);
         /* Buffered DO methods */
         // event
         void          BufferedDoCtrl_addDataTransmittedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener);
         void          BufferedDoCtrl_removeDataTransmittedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener);
         void          BufferedDoCtrl_addUnderrunListener(BufferedDoCtrl *_this, BfdDoEventListener *listener);
         void          BufferedDoCtrl_removeUnderrunListener(BufferedDoCtrl *_this, BfdDoEventListener *listener);
         void          BufferedDoCtrl_addCacheEmptiedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener);
         void          BufferedDoCtrl_removeCacheEmptiedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener);
         void          BufferedDoCtrl_addTransitStoppedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener);
         void          BufferedDoCtrl_removeTransitStoppedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener);
         void          BufferedDoCtrl_addStoppedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener);
         void          BufferedDoCtrl_removeStoppedListener(BufferedDoCtrl *_this, BfdDoEventListener *listener);
         // method           
         ErrorCode     BufferedDoCtrl_Prepare(BufferedDoCtrl *_this);
         ErrorCode     BufferedDoCtrl_RunOnce(BufferedDoCtrl *_this);
         ErrorCode     BufferedDoCtrl_Start(BufferedDoCtrl *_this);
         ErrorCode     BufferedDoCtrl_Stop(BufferedDoCtrl *_this, int32 action);
         ErrorCode     BufferedDoCtrl_SetData(BufferedDoCtrl *_this, int32 count, uint8 data[]);
         void          BufferedDoCtrl_Release(BufferedDoCtrl *_this);
         // property
         void*         BufferedDoCtrl_getBuffer(BufferedDoCtrl *_this);
         int32         BufferedDoCtrl_getBufferCapacity(BufferedDoCtrl *_this);
         ControlState  BufferedDoCtrl_getState(BufferedDoCtrl *_this);
         ScanPort*     BufferedDoCtrl_getScanPort(BufferedDoCtrl *_this);
         ConvertClock* BufferedDoCtrl_getConvertClock(BufferedDoCtrl *_this);
         Trigger*      BufferedDoCtrl_getTrigger(BufferedDoCtrl *_this);
         int8          BufferedDoCtrl_getStreaming(BufferedDoCtrl *_this);
         ErrorCode     BufferedDoCtrl_setStreaming(BufferedDoCtrl *_this, int8 value);

         // ----------------------------------------------------------
         // Counter Capability Indexer (method index: 470~472)
         // ----------------------------------------------------------
         void          CounterCapabilityIndexer_Dispose(CounterCapabilityIndexer *_this);
         int32         CounterCapabilityIndexer_getCount(CounterCapabilityIndexer *_this);
         ICollection*  CounterCapabilityIndexer_getItem(CounterCapabilityIndexer *_this, int32 channel);

         // ----------------------------------------------------------
         // Event Counter features (method index: 473~479)
         // ----------------------------------------------------------
         int32  EventCounterFeatures_getChannelCountMax(EventCounterFeatures *_this);
         int32  EventCounterFeatures_getResolution(EventCounterFeatures *_this);
         int32  EventCounterFeatures_getDataSize(EventCounterFeatures *_this);
         CounterCapabilityIndexer*  EventCounterFeatures_getCapabilities(EventCounterFeatures *_this);
         int8         EventCounterFeatures_getNoiseFilterSupported(EventCounterFeatures *_this);
         ICollection* EventCounterFeatures_getNoiseFilterOfChannels(EventCounterFeatures *_this);
         void         EventCounterFeatures_getNoiseFilterBlockTimeRange(EventCounterFeatures *_this, MathInterval *value);

         // ----------------------------------------------------------
         // EventCounterCtrl (method index: 480~504)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void        EventCounterCtrl_Dispose(EventCounterCtrl *_this);
         void        EventCounterCtrl_Cleanup(EventCounterCtrl *_this);
         ErrorCode   EventCounterCtrl_UpdateProperties(EventCounterCtrl *_this);
         void        EventCounterCtrl_addRemovedListener(EventCounterCtrl *_this, DeviceEventListener * listener);
         void        EventCounterCtrl_removeRemovedListener(EventCounterCtrl *_this, DeviceEventListener * listener);
         void        EventCounterCtrl_addReconnectedListener(EventCounterCtrl *_this, DeviceEventListener * listener);
         void        EventCounterCtrl_removeReconnectedListener(EventCounterCtrl *_this, DeviceEventListener * listener);
         void        EventCounterCtrl_addPropertyChangedListener(EventCounterCtrl *_this, DeviceEventListener * listener);
         void        EventCounterCtrl_removePropertyChangedListener(EventCounterCtrl *_this, DeviceEventListener * listener);
         void        EventCounterCtrl_getSelectedDevice(EventCounterCtrl *_this, DeviceInformation *x);
         ErrorCode   EventCounterCtrl_setSelectedDevice(EventCounterCtrl *_this, DeviceInformation const *x);
         int8        EventCounterCtrl_getInitialized(EventCounterCtrl *_this);
         int8        EventCounterCtrl_getCanEditProperty(EventCounterCtrl *_this);
         HANDLE      EventCounterCtrl_getDevice(EventCounterCtrl *_this);
         HANDLE      EventCounterCtrl_getModule(EventCounterCtrl *_this);
         ICollection* EventCounterCtrl_getSupportedDevices(EventCounterCtrl *_this);
         ICollection* EventCounterCtrl_getSupportedModes(EventCounterCtrl *_this);
         /* Methods derived from CntrCtrlBase */
         int32        EventCounterCtrl_getChannel(EventCounterCtrl *_this);
         ErrorCode    EventCounterCtrl_setChannel(EventCounterCtrl *_this, int32 ch);
         int8         EventCounterCtrl_getEnabled(EventCounterCtrl *_this);
         ErrorCode    EventCounterCtrl_setEnabled(EventCounterCtrl *_this, int8 enabled);
         int8         EventCounterCtrl_getRunning(EventCounterCtrl *_this);
         /* Methods derived from CntrCtrlExt */
         NoiseFilterChannel*   EventCounterCtrl_getNoiseFilter(EventCounterCtrl *_this);
         /* Event counter methods */
         EventCounterFeatures* EventCounterCtrl_getFeatures(EventCounterCtrl *_this);
         int32                 EventCounterCtrl_getValue(EventCounterCtrl *_this);

         // ----------------------------------------------------------
         // Frequency meter features (method index: 505~512)
         // ----------------------------------------------------------
         int32  FreqMeterFeatures_getChannelCountMax(FreqMeterFeatures *_this);
         int32  FreqMeterFeatures_getResolution(FreqMeterFeatures *_this);
         int32  FreqMeterFeatures_getDataSize(FreqMeterFeatures *_this);
         CounterCapabilityIndexer*  FreqMeterFeatures_getCapabilities(FreqMeterFeatures *_this);
         int8          FreqMeterFeatures_getNoiseFilterSupported(FreqMeterFeatures *_this);
         ICollection*  FreqMeterFeatures_getNoiseFilterOfChannels(FreqMeterFeatures *_this);
         void          FreqMeterFeatures_getNoiseFilterBlockTimeRange(FreqMeterFeatures *_this, MathInterval *value);
         ICollection*  FreqMeterFeatures_getFmMethods(FreqMeterFeatures *_this);

         // ----------------------------------------------------------
         // FreqMeterCtrl (method index: 513~541)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void        FreqMeterCtrl_Dispose(FreqMeterCtrl *_this);
         void        FreqMeterCtrl_Cleanup(FreqMeterCtrl *_this);
         ErrorCode   FreqMeterCtrl_UpdateProperties(FreqMeterCtrl *_this);
         void        FreqMeterCtrl_addRemovedListener(FreqMeterCtrl *_this, DeviceEventListener * listener);
         void        FreqMeterCtrl_removeRemovedListener(FreqMeterCtrl *_this, DeviceEventListener * listener);
         void        FreqMeterCtrl_addReconnectedListener(FreqMeterCtrl *_this, DeviceEventListener * listener);
         void        FreqMeterCtrl_removeReconnectedListener(FreqMeterCtrl *_this, DeviceEventListener * listener);
         void        FreqMeterCtrl_addPropertyChangedListener(FreqMeterCtrl *_this, DeviceEventListener * listener);
         void        FreqMeterCtrl_removePropertyChangedListener(FreqMeterCtrl *_this, DeviceEventListener * listener);
         void        FreqMeterCtrl_getSelectedDevice(FreqMeterCtrl *_this, DeviceInformation *x);
         ErrorCode   FreqMeterCtrl_setSelectedDevice(FreqMeterCtrl *_this, DeviceInformation const *x);
         int8        FreqMeterCtrl_getInitialized(FreqMeterCtrl *_this);
         int8        FreqMeterCtrl_getCanEditProperty(FreqMeterCtrl *_this);
         HANDLE      FreqMeterCtrl_getDevice(FreqMeterCtrl *_this);
         HANDLE      FreqMeterCtrl_getModule(FreqMeterCtrl *_this);
         ICollection*  FreqMeterCtrl_getSupportedDevices(FreqMeterCtrl *_this);
         ICollection*  FreqMeterCtrl_getSupportedModes(FreqMeterCtrl *_this);
         /* Methods derived from CntrCtrlBase */                                                                               
         int32         FreqMeterCtrl_getChannel(FreqMeterCtrl *_this);
         ErrorCode     FreqMeterCtrl_setChannel(FreqMeterCtrl *_this, int32 ch);
         int8          FreqMeterCtrl_getEnabled(FreqMeterCtrl *_this);
         ErrorCode     FreqMeterCtrl_setEnabled(FreqMeterCtrl *_this, int8 enabled);
         int8          FreqMeterCtrl_getRunning(FreqMeterCtrl *_this);
         /* Methods derived from CntrCtrlExt */                                                                                
         NoiseFilterChannel* FreqMeterCtrl_getNoiseFilter(FreqMeterCtrl *_this);
         /* Frequency meter methods */
         FreqMeterFeatures*  FreqMeterCtrl_getFeatures(FreqMeterCtrl *_this);
         double              FreqMeterCtrl_getValue(FreqMeterCtrl *_this);
         FreqMeasureMethod   FreqMeterCtrl_getMethod(FreqMeterCtrl *_this);
         ErrorCode           FreqMeterCtrl_setMethod(FreqMeterCtrl *_this, FreqMeasureMethod value);
         double              FreqMeterCtrl_getCollectionPeriod(FreqMeterCtrl *_this);
         ErrorCode           FreqMeterCtrl_setCollectionPeriod(FreqMeterCtrl *_this, double value);

         // ----------------------------------------------------------
         // One shot features (method index: 542~549)
         // ----------------------------------------------------------
         int32  OneShotFeatures_getChannelCountMax(OneShotFeatures *_this);
         int32  OneShotFeatures_getResolution(OneShotFeatures *_this);
         int32  OneShotFeatures_getDataSize(OneShotFeatures *_this);
         CounterCapabilityIndexer*  OneShotFeatures_getCapabilities(OneShotFeatures *_this);
         int8          OneShotFeatures_getNoiseFilterSupported(OneShotFeatures *_this);
         ICollection*  OneShotFeatures_getNoiseFilterOfChannels(OneShotFeatures *_this);
         void          OneShotFeatures_getNoiseFilterBlockTimeRange(OneShotFeatures *_this, MathInterval *value);
         void          OneShotFeatures_getDelayCountRange(OneShotFeatures *_this, MathInterval *value);

         // ----------------------------------------------------------
         // OneShotCtrl (method index: 550~577)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       OneShotCtrl_Dispose(OneShotCtrl *_this);
         void       OneShotCtrl_Cleanup(OneShotCtrl *_this);
         ErrorCode  OneShotCtrl_UpdateProperties(OneShotCtrl *_this);
         void       OneShotCtrl_addRemovedListener(OneShotCtrl *_this, DeviceEventListener * listener);
         void       OneShotCtrl_removeRemovedListener(OneShotCtrl *_this, DeviceEventListener * listener);
         void       OneShotCtrl_addReconnectedListener(OneShotCtrl *_this, DeviceEventListener * listener);
         void       OneShotCtrl_removeReconnectedListener(OneShotCtrl *_this, DeviceEventListener * listener);
         void       OneShotCtrl_addPropertyChangedListener(OneShotCtrl *_this, DeviceEventListener * listener);
         void       OneShotCtrl_removePropertyChangedListener(OneShotCtrl *_this, DeviceEventListener * listener);
         void       OneShotCtrl_getSelectedDevice(OneShotCtrl *_this, DeviceInformation *x);
         ErrorCode  OneShotCtrl_setSelectedDevice(OneShotCtrl *_this, DeviceInformation const *x);
         int8       OneShotCtrl_getInitialized(OneShotCtrl *_this);
         int8       OneShotCtrl_getCanEditProperty(OneShotCtrl *_this);
         HANDLE     OneShotCtrl_getDevice(OneShotCtrl *_this);
         HANDLE     OneShotCtrl_getModule(OneShotCtrl *_this);
         ICollection* OneShotCtrl_getSupportedDevices(OneShotCtrl *_this);
         ICollection* OneShotCtrl_getSupportedModes(OneShotCtrl *_this);
         /* Methods derived from CntrCtrlBase */                                                                            
         int32        OneShotCtrl_getChannel(OneShotCtrl *_this);
         ErrorCode    OneShotCtrl_setChannel(OneShotCtrl *_this, int32 ch);
         int8         OneShotCtrl_getEnabled(OneShotCtrl *_this);
         ErrorCode    OneShotCtrl_setEnabled(OneShotCtrl *_this, int8 enabled);
         int8         OneShotCtrl_getRunning(OneShotCtrl *_this);
         /* Methods derived from CntrCtrlExt */                                                                             
         NoiseFilterChannel* OneShotCtrl_getNoiseFilter(OneShotCtrl *_this);
         /* one shot methods */
         void             OneShotCtrl_addOneShotListener(OneShotCtrl *_this, CntrEventListener * listener);
         void             OneShotCtrl_removeOneShotListener(OneShotCtrl *_this, CntrEventListener * listener);
         OneShotFeatures* OneShotCtrl_getFeatures(OneShotCtrl *_this);
         int32            OneShotCtrl_getDelayCount(OneShotCtrl *_this);
         ErrorCode        OneShotCtrl_setDelayCount(OneShotCtrl *_this, int32 value);

         // ----------------------------------------------------------
         // Timer/Pulse features (method index: 578~586)
         // ----------------------------------------------------------
         int32  TimerPulseFeatures_getChannelCountMax(TimerPulseFeatures *_this);
         int32  TimerPulseFeatures_getResolution(TimerPulseFeatures *_this);
         int32  TimerPulseFeatures_getDataSize(TimerPulseFeatures *_this);
         CounterCapabilityIndexer*  TimerPulseFeatures_getCapabilities(TimerPulseFeatures *_this);
         int8         TimerPulseFeatures_getNoiseFilterSupported(TimerPulseFeatures *_this);
         ICollection* TimerPulseFeatures_getNoiseFilterOfChannels(TimerPulseFeatures *_this);
         void         TimerPulseFeatures_getNoiseFilterBlockTimeRange(TimerPulseFeatures *_this, MathInterval *value);
         void         TimerPulseFeatures_getTimerFrequencyRange(TimerPulseFeatures *_this, MathInterval *value);
         int8         TimerPulseFeatures_getTimerEventSupported(TimerPulseFeatures *_this);

         // ----------------------------------------------------------
         // TimerPulseCtrl (method index: 587~614)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       TimerPulseCtrl_Dispose(TimerPulseCtrl *_this);
         void       TimerPulseCtrl_Cleanup(TimerPulseCtrl *_this);
         ErrorCode  TimerPulseCtrl_UpdateProperties(TimerPulseCtrl *_this);
         void       TimerPulseCtrl_addRemovedListener(TimerPulseCtrl *_this, DeviceEventListener * listener);
         void       TimerPulseCtrl_removeRemovedListener(TimerPulseCtrl *_this, DeviceEventListener * listener);
         void       TimerPulseCtrl_addReconnectedListener(TimerPulseCtrl *_this, DeviceEventListener * listener);
         void       TimerPulseCtrl_removeReconnectedListener(TimerPulseCtrl *_this, DeviceEventListener * listener);
         void       TimerPulseCtrl_addPropertyChangedListener(TimerPulseCtrl *_this, DeviceEventListener * listener);
         void       TimerPulseCtrl_removePropertyChangedListener(TimerPulseCtrl *_this, DeviceEventListener * listener);
         void       TimerPulseCtrl_getSelectedDevice(TimerPulseCtrl *_this, DeviceInformation *x);
         ErrorCode  TimerPulseCtrl_setSelectedDevice(TimerPulseCtrl *_this, DeviceInformation const *x);
         int8       TimerPulseCtrl_getInitialized(TimerPulseCtrl *_this);
         int8       TimerPulseCtrl_getCanEditProperty(TimerPulseCtrl *_this);
         HANDLE     TimerPulseCtrl_getDevice(TimerPulseCtrl *_this);
         HANDLE     TimerPulseCtrl_getModule(TimerPulseCtrl *_this);
         ICollection*  TimerPulseCtrl_getSupportedDevices(TimerPulseCtrl *_this);
         ICollection*  TimerPulseCtrl_getSupportedModes(TimerPulseCtrl *_this);
         /* Methods derived from CntrCtrlBase */                                                                                
         int32         TimerPulseCtrl_getChannel(TimerPulseCtrl *_this);
         ErrorCode     TimerPulseCtrl_setChannel(TimerPulseCtrl *_this, int32 ch);
         int8          TimerPulseCtrl_getEnabled(TimerPulseCtrl *_this);
         ErrorCode     TimerPulseCtrl_setEnabled(TimerPulseCtrl *_this, int8 enabled);
         int8          TimerPulseCtrl_getRunning(TimerPulseCtrl *_this);
         /* Methods derived from CntrCtrlExt */                                                                                 
         NoiseFilterChannel* TimerPulseCtrl_getNoiseFilter(TimerPulseCtrl *_this);
         /* timer pulse methods */
         void          TimerPulseCtrl_addTimerTickListener(TimerPulseCtrl *_this, CntrEventListener * listener);
         void          TimerPulseCtrl_removeTimerTickListener(TimerPulseCtrl *_this, CntrEventListener * listener);
         TimerPulseFeatures*  TimerPulseCtrl_getFeatures(TimerPulseCtrl *_this);
         double        TimerPulseCtrl_getFrequency(TimerPulseCtrl *_this);
         ErrorCode     TimerPulseCtrl_setFrequency(TimerPulseCtrl *_this, double value);

         // ----------------------------------------------------------
         // Pulse width meter features (method index: 615~623)
         // ----------------------------------------------------------
         int32  PwMeterFeatures_getChannelCountMax(PwMeterFeatures *_this);
         int32  PwMeterFeatures_getResolution(PwMeterFeatures *_this);
         int32  PwMeterFeatures_getDataSize(PwMeterFeatures *_this);
         CounterCapabilityIndexer*  PwMeterFeatures_getCapabilities(PwMeterFeatures *_this);
         int8         PwMeterFeatures_getNoiseFilterSupported(PwMeterFeatures *_this);
         ICollection* PwMeterFeatures_getNoiseFilterOfChannels(PwMeterFeatures *_this);
         void         PwMeterFeatures_getNoiseFilterBlockTimeRange(PwMeterFeatures *_this, MathInterval *value);
         ICollection* PwMeterFeatures_getPwmCascadeGroup(PwMeterFeatures *_this);
         int8         PwMeterFeatures_getOverflowEventSupported(PwMeterFeatures *_this);

         // ----------------------------------------------------------
         // PwMeterCtrl (method index: 624~650)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       PwMeterCtrl_Dispose(PwMeterCtrl *_this);
         void       PwMeterCtrl_Cleanup(PwMeterCtrl *_this);
         ErrorCode  PwMeterCtrl_UpdateProperties(PwMeterCtrl *_this);
         void       PwMeterCtrl_addRemovedListener(PwMeterCtrl *_this, DeviceEventListener * listener);
         void       PwMeterCtrl_removeRemovedListener(PwMeterCtrl *_this, DeviceEventListener * listener);
         void       PwMeterCtrl_addReconnectedListener(PwMeterCtrl *_this, DeviceEventListener * listener);
         void       PwMeterCtrl_removeReconnectedListener(PwMeterCtrl *_this, DeviceEventListener * listener);
         void       PwMeterCtrl_addPropertyChangedListener(PwMeterCtrl *_this, DeviceEventListener * listener);
         void       PwMeterCtrl_removePropertyChangedListener(PwMeterCtrl *_this, DeviceEventListener * listener);
         void       PwMeterCtrl_getSelectedDevice(PwMeterCtrl *_this, DeviceInformation *x);
         ErrorCode  PwMeterCtrl_setSelectedDevice(PwMeterCtrl *_this, DeviceInformation const *x);
         int8       PwMeterCtrl_getInitialized(PwMeterCtrl *_this);
         int8       PwMeterCtrl_getCanEditProperty(PwMeterCtrl *_this);
         HANDLE     PwMeterCtrl_getDevice(PwMeterCtrl *_this);
         HANDLE     PwMeterCtrl_getModule(PwMeterCtrl *_this);
         ICollection*  PwMeterCtrl_getSupportedDevices(PwMeterCtrl *_this);
         ICollection*  PwMeterCtrl_getSupportedModes(PwMeterCtrl *_this);
         /* Methods derived from CntrCtrlBase */                                                                           
         int32      PwMeterCtrl_getChannel(PwMeterCtrl *_this);
         ErrorCode  PwMeterCtrl_setChannel(PwMeterCtrl *_this, int32 ch);
         int8       PwMeterCtrl_getEnabled(PwMeterCtrl *_this);
         ErrorCode  PwMeterCtrl_setEnabled(PwMeterCtrl *_this, int8 enabled);
         int8       PwMeterCtrl_getRunning(PwMeterCtrl *_this);
         /* Methods derived from CntrCtrlExt */                                                                            
         NoiseFilterChannel*  PwMeterCtrl_getNoiseFilter(PwMeterCtrl *_this);
         /* Pulse width meter methods */
         void       PwMeterCtrl_addOverflowListener(PwMeterCtrl *_this, CntrEventListener * listener);
         void       PwMeterCtrl_removeOverflowListener(PwMeterCtrl *_this, CntrEventListener * listener);
         PwMeterFeatures*  PwMeterCtrl_getFeatures(PwMeterCtrl *_this);
         void       PwMeterCtrl_getValue(PwMeterCtrl *_this, PulseWidth *width);

         // ----------------------------------------------------------
         // Pulse width modulator features (method index: 651~659)
         // ----------------------------------------------------------
         int32  PwModulatorFeatures_getChannelCountMax(PwModulatorFeatures *_this);
         int32  PwModulatorFeatures_getResolution(PwModulatorFeatures *_this);
         int32  PwModulatorFeatures_getDataSize(PwModulatorFeatures *_this);
         CounterCapabilityIndexer*  PwModulatorFeatures_getCapabilities(PwModulatorFeatures *_this);
         int8   PwModulatorFeatures_getNoiseFilterSupported(PwModulatorFeatures *_this);
         ICollection*  PwModulatorFeatures_getNoiseFilterOfChannels(PwModulatorFeatures *_this);
         void   PwModulatorFeatures_getNoiseFilterBlockTimeRange(PwModulatorFeatures *_this, MathInterval *value);
         void   PwModulatorFeatures_getHiPeriodRange(PwModulatorFeatures *_this, MathInterval *value);
         void   PwModulatorFeatures_getLoPeriodRange(PwModulatorFeatures *_this, MathInterval *value);

         // ----------------------------------------------------------
         // PwModulatorCtrl (method index: 660~685)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       PwModulatorCtrl_Dispose(PwModulatorCtrl *_this);
         void       PwModulatorCtrl_Cleanup(PwModulatorCtrl *_this);
         ErrorCode  PwModulatorCtrl_UpdateProperties(PwModulatorCtrl *_this);
         void       PwModulatorCtrl_addRemovedListener(PwModulatorCtrl *_this, DeviceEventListener * listener);
         void       PwModulatorCtrl_removeRemovedListener(PwModulatorCtrl *_this, DeviceEventListener * listener);
         void       PwModulatorCtrl_addReconnectedListener(PwModulatorCtrl *_this, DeviceEventListener * listener);
         void       PwModulatorCtrl_removeReconnectedListener(PwModulatorCtrl *_this, DeviceEventListener * listener);
         void       PwModulatorCtrl_addPropertyChangedListener(PwModulatorCtrl *_this, DeviceEventListener * listener);
         void       PwModulatorCtrl_removePropertyChangedListener(PwModulatorCtrl *_this, DeviceEventListener * listener);
         void       PwModulatorCtrl_getSelectedDevice(PwModulatorCtrl *_this, DeviceInformation *x);
         ErrorCode  PwModulatorCtrl_setSelectedDevice(PwModulatorCtrl *_this, DeviceInformation const *x);
         int8       PwModulatorCtrl_getInitialized(PwModulatorCtrl *_this);
         int8       PwModulatorCtrl_getCanEditProperty(PwModulatorCtrl *_this);
         HANDLE     PwModulatorCtrl_getDevice(PwModulatorCtrl *_this);
         HANDLE     PwModulatorCtrl_getModule(PwModulatorCtrl *_this);
         ICollection*  PwModulatorCtrl_getSupportedDevices(PwModulatorCtrl *_this);
         ICollection*  PwModulatorCtrl_getSupportedModes(PwModulatorCtrl *_this);
         /* Methods derived from CntrCtrlBase */                                                                                  
         int32      PwModulatorCtrl_getChannel(PwModulatorCtrl *_this);
         ErrorCode  PwModulatorCtrl_setChannel(PwModulatorCtrl *_this, int32 ch);
         int8       PwModulatorCtrl_getEnabled(PwModulatorCtrl *_this);
         ErrorCode  PwModulatorCtrl_setEnabled(PwModulatorCtrl *_this, int8 enabled);
         int8       PwModulatorCtrl_getRunning(PwModulatorCtrl *_this);
         /* Methods derived from CntrCtrlExt */                                                                                   
         NoiseFilterChannel*  PwModulatorCtrl_getNoiseFilter(PwModulatorCtrl *_this);
         /* Pulse width modulator methods */
         PwModulatorFeatures* PwModulatorCtrl_getFeatures(PwModulatorCtrl *_this);
         void       PwModulatorCtrl_getPulseWidth(PwModulatorCtrl *_this, PulseWidth *width);
         ErrorCode  PwModulatorCtrl_setPulseWidth(PwModulatorCtrl *_this, PulseWidth *width);

         // ----------------------------------------------------------
         // Up-Down counter features (method index: 686~695)
         // ----------------------------------------------------------
         int32  UdCounterFeatures_getChannelCountMax(UdCounterFeatures *_this);
         int32  UdCounterFeatures_getResolution(UdCounterFeatures *_this);
         int32  UdCounterFeatures_getDataSize(UdCounterFeatures *_this);
         CounterCapabilityIndexer*  UdCounterFeatures_getCapabilities(UdCounterFeatures *_this);
         int8          UdCounterFeatures_getNoiseFilterSupported(UdCounterFeatures *_this);
         ICollection*  UdCounterFeatures_getNoiseFilterOfChannels(UdCounterFeatures *_this);
         void          UdCounterFeatures_getNoiseFilterBlockTimeRange(UdCounterFeatures *_this, MathInterval *value);
         ICollection*  UdCounterFeatures_getCountingTypes(UdCounterFeatures *_this);
         ICollection*  UdCounterFeatures_getInitialValues(UdCounterFeatures *_this);
         ICollection*  UdCounterFeatures_getSnapEventSources(UdCounterFeatures *_this);

         // ----------------------------------------------------------
         // UdCounterCtrl (method index: 696~734)
         // ----------------------------------------------------------
         /* Methods derived from DeviceCtrlBase */
         void       UdCounterCtrl_Dispose(UdCounterCtrl *_this);
         void       UdCounterCtrl_Cleanup(UdCounterCtrl *_this);
         ErrorCode  UdCounterCtrl_UpdateProperties(UdCounterCtrl *_this);
         void       UdCounterCtrl_addRemovedListener(UdCounterCtrl *_this, DeviceEventListener * listener);
         void       UdCounterCtrl_removeRemovedListener(UdCounterCtrl *_this, DeviceEventListener * listener);
         void       UdCounterCtrl_addReconnectedListener(UdCounterCtrl *_this, DeviceEventListener * listener);
         void       UdCounterCtrl_removeReconnectedListener(UdCounterCtrl *_this, DeviceEventListener * listener);
         void       UdCounterCtrl_addPropertyChangedListener(UdCounterCtrl *_this, DeviceEventListener * listener);
         void       UdCounterCtrl_removePropertyChangedListener(UdCounterCtrl *_this, DeviceEventListener * listener);
         void       UdCounterCtrl_getSelectedDevice(UdCounterCtrl *_this, DeviceInformation *x);
         ErrorCode  UdCounterCtrl_setSelectedDevice(UdCounterCtrl *_this, DeviceInformation const *x);
         int8       UdCounterCtrl_getInitialized(UdCounterCtrl *_this);
         int8       UdCounterCtrl_getCanEditProperty(UdCounterCtrl *_this);
         HANDLE     UdCounterCtrl_getDevice(UdCounterCtrl *_this);
         HANDLE     UdCounterCtrl_getModule(UdCounterCtrl *_this);
         ICollection*  UdCounterCtrl_getSupportedDevices(UdCounterCtrl *_this);
         ICollection*  UdCounterCtrl_getSupportedModes(UdCounterCtrl *_this);
         /* Methods derived from CntrCtrlBase */                                                                              
         int32      UdCounterCtrl_getChannel(UdCounterCtrl *_this);
         ErrorCode  UdCounterCtrl_setChannel(UdCounterCtrl *_this, int32 ch);
         int8       UdCounterCtrl_getEnabled(UdCounterCtrl *_this);
         ErrorCode  UdCounterCtrl_setEnabled(UdCounterCtrl *_this, int8 enabled);
         int8       UdCounterCtrl_getRunning(UdCounterCtrl *_this);
         /* Methods derived from CntrCtrlExt */                                                                               
         NoiseFilterChannel*  UdCounterCtrl_getNoiseFilter(UdCounterCtrl *_this);
         /* up-down counter methods */
         void       UdCounterCtrl_addUdCntrEventListener(UdCounterCtrl *_this, UdCntrEventListener * listener);
         void       UdCounterCtrl_removeUdCntrEventListener(UdCounterCtrl *_this, UdCntrEventListener * listener);
         ErrorCode  UdCounterCtrl_SnapStart(UdCounterCtrl *_this, int32 srcId);
         ErrorCode  UdCounterCtrl_SnapStop(UdCounterCtrl *_this, int32 srcId);
         ErrorCode  UdCounterCtrl_CompareSetTable(UdCounterCtrl *_this, int32 count, int32 *table);
         ErrorCode  UdCounterCtrl_CompareSetInterval(UdCounterCtrl *_this, int32 start, int32 increment,int32 count);
         ErrorCode  UdCounterCtrl_CompareClear(UdCounterCtrl *_this);
         ErrorCode  UdCounterCtrl_ValueReset(UdCounterCtrl *_this);

         UdCounterFeatures*  UdCounterCtrl_getFeatures(UdCounterCtrl *_this);
         int32               UdCounterCtrl_getValue(UdCounterCtrl *_this);
         SignalCountingType  UdCounterCtrl_getCountingType(UdCounterCtrl *_this);
         ErrorCode           UdCounterCtrl_setCountingType(UdCounterCtrl *_this, SignalCountingType value);
         int32               UdCounterCtrl_getInitialValue(UdCounterCtrl *_this);
         ErrorCode           UdCounterCtrl_setInitialValue(UdCounterCtrl *_this, int32 value);
         int32               UdCounterCtrl_getResetTimesByIndex(UdCounterCtrl *_this);
         ErrorCode           UdCounterCtrl_setResetTimesByIndex(UdCounterCtrl *_this, int32 value);

         /* BufferedAiCtrl new methods*/
         // event
         void       BufferedAiCtrl_addBurnOutListener(BufferedAiCtrl *_this, BfdAiEventListener *listener);
         void       BufferedAiCtrl_removeBurnOutListener(BufferedAiCtrl *_this, BfdAiEventListener *listener);
       
#        endif

#     ifdef __cplusplus
      }
#     endif
#  endif

#endif // _BIONIC_DAQ_DLL

END_NAMEAPCE_AUTOMATION_BDAQ

#endif // _BDAQ_COM_LIKE_CLASS_LIB

