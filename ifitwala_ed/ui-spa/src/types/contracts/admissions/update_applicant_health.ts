// ifitwala_ed/ui-spa/src/types/contracts/admissions/update_applicant_health.ts

export type Request = {
  student_applicant?: string
  blood_group: string
  allergies: boolean
  food_allergies: string
  insect_bites: string
  medication_allergies: string
  asthma: string
  bladder__bowel_problems: string
  diabetes: string
  headache_migraine: string
  high_blood_pressure: string
  seizures: string
  bone_joints_scoliosis: string
  blood_disorder_info: string
  fainting_spells: string
  hearing_problems: string
  recurrent_ear_infections: string
  speech_problem: string
  birth_defect: string
  dental_problems: string
  g6pd: string
  heart_problems: string
  recurrent_nose_bleeding: string
  vision_problem: string
  diet_requirements: string
  medical_surgeries__hospitalizations: string
  other_medical_information: string
  vaccinations: {
    vaccine_name: string
    date: string
    vaccination_proof: string
    additional_notes: string
  }[]
}

export type Response = {
  ok: boolean
}
