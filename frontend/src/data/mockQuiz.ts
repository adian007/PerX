import type { QuizQuestion } from '@/types'

export const QUIZ_BY_CATEGORY: Record<string, QuizQuestion[]> = {
  fitness: [
    {
      id: 'f1',
      question:
        'Subvencionet e punëdhënësit për palestrë janë zakonisht pa tatim deri në 50.000 lekë në vit në shumë vende të Evropës.',
      answer: true,
      fact: 'Në shumicën e programeve të mirëqenies korporative, subvencionet e palestrës deri në 50.000 lekë/vit përjashtohen nga tatimi kur ofrohen si përfitim i strukturuar.',
    },
    {
      id: 'f2',
      question: 'Duhet të përdorësh përfitimin e palestrës vetëm në një vend të caktuar.',
      answer: false,
      fact: 'Shumica e përfitimeve fitness në PerX ofrojnë qasje në rrjet. Karta jote funksionon zakonisht në 200+ vende partner, jo vetëm në një palestër.',
    },
    {
      id: 'f3',
      question: 'Alokimi i papërdorur i palestrës kalon automatikisht në vitin tjetër të përfitimeve.',
      answer: false,
      fact: 'Alokimet e palestrës zakonisht rivendosen çdo vit. Kontrollo afatin e regjistrimit. Disa punëdhënës lejojnë ndryshime vetëm gjatë regjistrimit.',
    },
  ],
  wellness: [
    {
      id: 'w1',
      question: 'Kontributet shëndetësore nga paga zbriten para tatimit mbi të ardhurat.',
      answer: true,
      fact: 'Kontributet shëndetësore që punëdhënësi mbulon përmes pagës zbriten para tatimit mbi të ardhurat.',
    },
    {
      id: 'w2',
      question: 'Pikët e programit të mirëqenies skadojnë në fund të çdo muaji kalendarik.',
      answer: false,
      fact: 'Pikët e mirëqenies në PerX grumbullohen gjatë vitit të përfitimeve. Bonuset e serisë ditore aplikohen çdo ditë, por bilanci i pikëve mbetet.',
    },
    {
      id: 'w3',
      question: 'Aplikacionet e shëndetit mendor të mbuluara kërkojnë referim mjeku.',
      answer: false,
      fact: 'Përfitimet dixhitale si aplikacionet e meditimit zakonisht regjistrohen vetë, pa referim mjeku. Aktivizo direkt nga paneli PerX.',
    },
  ],
  food: [
    {
      id: 'fd1',
      question: 'Subvencionet e ushqimit konsiderohen të ardhura tatimore në të gjitha vendet.',
      answer: false,
      fact: 'Shumë vende trajtojnë kuponët e ushqimit dhe subvencionet si jo-tatimore deri në limite mujore specifike (shpesh 800–1.500 lekë në ditë).',
    },
    {
      id: 'fd2',
      question: 'Përfitimet e dërgesës së ushqimit mund të përdoren vetëm për drekë.',
      answer: false,
      fact: 'Partnerët e ushqimit në PerX pranojnë porosi në çdo kohë: mëngjes, drekë ose darkë.',
    },
  ],
  finance: [
    {
      id: 'fn1',
      question: 'Kontributet shëndetësore të papërdorura mbeten në llogarinë tënde vit pas viti.',
      answer: true,
      fact: 'Ndryshe nga disa programe me afat, kontributet shëndetësore të strukturuara shpesh mbeten dhe grumbullohen për shpenzime të ardhshme.',
    },
    {
      id: 'fn2',
      question: 'Mund të tërheqësh kontribute shëndetësore për shpenzime jo-mjekësore pa kufizime.',
      answer: false,
      fact: 'Tërheqjet për shpenzime jo-mjekësore kanë rregulla dhe kufizime tatimore. Kontrollo programin e punëdhënësit tënd.',
    },
  ],
  default: [
    {
      id: 'd1',
      question: 'Zgjedhjet e përfitimeve kërkojnë miratimin e punëdhënësit para aktivizimit.',
      answer: true,
      fact: 'PerX i drejton të gjitha zgjedhjet në radhën e miratimit të punëdhënësit. Buxheti rezervohet menjëherë; aktivizimi vjen pas miratimit.',
    },
    {
      id: 'd2',
      question: 'Mund të ndryshosh zgjedhjet e përfitimeve pa kufi çdo muaj.',
      answer: false,
      fact: 'Shumica e punëdhënësve lejojnë një zgjedhje aktive për kategori në muaj. Ndryshimet gjatë regjistrimit janë të pakufizuara.',
    },
    {
      id: 'd3',
      question: 'Pikët PerX nga pyetësorët shpërblehen me përfitime shtesë.',
      answer: true,
      fact: 'Pikët grumbullohen në bilancin tënd dhe hapin përfitime bonus, distinktiva arritjesh dhe qasje prioritare gjatë regjistrimit.',
    },
  ],
}

export function getQuizQuestions(category?: string): QuizQuestion[] {
  if (category && QUIZ_BY_CATEGORY[category]) {
    return QUIZ_BY_CATEGORY[category]
  }
  return QUIZ_BY_CATEGORY.default
}
