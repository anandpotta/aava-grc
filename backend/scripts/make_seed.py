"""Generate the seed JSON used by the demo tenant.

Run:  python scripts/make_seed.py
"""
import json
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "app" / "data" / "seed"
SEED.mkdir(parents=True, exist_ok=True)

JURISDICTIONS = [
    {"id": "us", "name": "US regulations", "short": "US", "regulators": "FinCEN · OCC · CFPB · SEC"},
    {"id": "ca", "name": "Canada", "short": "CA", "regulators": "OSFI · FINTRAC · FCAC"},
    {"id": "uk", "name": "United Kingdom", "short": "UK", "regulators": "FCA · PRA · ICO"},
    {"id": "eu", "name": "European Union", "short": "EU", "regulators": "EBA · ECB · EDPB"},
    {"id": "in", "name": "India", "short": "IN", "regulators": "RBI · SEBI · MeitY"},
    {"id": "cn", "name": "China", "short": "CN", "regulators": "PBoC · NFRA · CAC"},
    {"id": "jp", "name": "Japan", "short": "JP", "regulators": "JFSA · PPC"},
    {"id": "hk", "name": "Hong Kong", "short": "HK", "regulators": "HKMA · SFC · PCPD"},
    {"id": "kr", "name": "South Korea", "short": "KR", "regulators": "FSC · FSS · PIPC"},
    {"id": "sg", "name": "Singapore", "short": "SG", "regulators": "MAS · PDPC"},
    {"id": "sa", "name": "Saudi Arabia", "short": "SA", "regulators": "SAMA · CMA"},
    {"id": "af", "name": "Africa (ZA, NG, KE)", "short": "AF", "regulators": "SARB · CBN · CBK"},
]

FRAMEWORKS = [
    {"id": "gdpr", "name": "GDPR", "sub": "EU data protection"},
    {"id": "hipaa", "name": "HIPAA", "sub": "US health privacy"},
    {"id": "dpdp", "name": "DPDP Act", "sub": "India data protection"},
    {"id": "pcidss", "name": "PCI DSS 4.0", "sub": "Card data security"},
    {"id": "basel", "name": "Basel III / IV", "sub": "Capital and liquidity"},
    {"id": "nistcsf", "name": "NIST CSF 2.0", "sub": "Cyber framework"},
    {"id": "fatf", "name": "FATF 40 Recommendations", "sub": "AML/CFT standards"},
    {"id": "dora", "name": "DORA", "sub": "EU operational resilience"},
]

RULE_MATTERS = [
    "AML / CFT", "KYC and CDD", "Sanctions screening", "Consumer protection",
    "Capital and liquidity", "Outsourcing and third party", "Operational resilience",
    "Data privacy", "Data localisation", "Conduct and culture", "Regulatory reporting",
    "Fraud and payments", "Cyber security", "Governance and accountability",
    "Complaints handling", "Records and retention",
]
RULE_TYPES = [
    "Act / Statute", "Regulation", "Rule", "Master Direction", "Guideline",
    "Circular", "Supervisory expectation", "Code of practice", "Standard", "Notice", "Directive",
]
FW_TAGS = {
    "AML / CFT": ["fatf"], "KYC and CDD": ["fatf"], "Sanctions screening": ["fatf"],
    "Data privacy": ["gdpr", "dpdp"], "Data localisation": ["dpdp"],
    "Cyber security": ["nistcsf", "pcidss"], "Operational resilience": ["dora", "nistcsf"],
    "Capital and liquidity": ["basel"], "Fraud and payments": ["pcidss"],
}

R = [
    ("us","FinCEN","31 CFR 1020.220","Customer identification programme for banks","Regulation","KYC and CDD","2024-04-01","A bank must implement a written Customer Identification Programme that includes risk-based procedures to verify the identity of each customer before opening an account, and must retain the identifying information used.",4,"High"),
    ("us","FinCEN","31 CFR 1010.230","Beneficial ownership requirements for legal entity customers","Regulation","KYC and CDD","2024-04-01","A covered financial institution must establish and maintain written procedures reasonably designed to identify and verify beneficial owners of legal entity customers at the time a new account is opened.",5,"High"),
    ("us","FinCEN","31 CFR 1020.320","Reports of suspicious transactions","Regulation","AML / CFT","2023-09-15","A bank shall file a suspicious activity report no later than 30 calendar days after the date of initial detection of facts that may constitute a basis for filing, and shall not notify any person involved that a report was filed.",3,"Critical"),
    ("us","OFAC","31 CFR 501.603","Blocked property and rejected transaction reporting","Regulation","Sanctions screening","2024-01-10","Any person holding blocked property must report to OFAC within 10 business days of blocking, and must file an annual report of blocked property held as of 30 June each year.",3,"High"),
    ("us","CFPB","12 CFR 1005.11","Error resolution procedures for electronic fund transfers","Regulation","Consumer protection","2023-06-30","A financial institution shall investigate promptly and determine whether an error occurred within 10 business days of receiving a notice of error, and shall report the results to the consumer within three business days of completing the investigation.",4,"Medium"),
    ("us","CFPB","12 CFR 1002.12","Record retention under Regulation B","Regulation","Records and retention","2017-10-02","For 25 months after the date that a creditor notifies an applicant of action taken on an application or of incompleteness, the creditor shall retain in original form or a copy thereof any application that it receives and any written or recorded information used in evaluating the application.",5,"Medium"),
    ("us","OCC","12 CFR 30 App. D","Heightened standards for risk governance frameworks","Guideline","Governance and accountability","2022-11-01","A covered bank should establish and adhere to a written risk governance framework that includes independent risk management and internal audit, with the board providing active oversight and credible challenge of management.",6,"High"),
    ("us","OCC","OCC Bulletin 2023-17","Third-party relationships: interagency risk management guidance","Guideline","Outsourcing and third party","2023-06-06","A banking organisation should conduct due diligence before entering a third-party relationship, maintain written contracts addressing performance and audit rights, and conduct ongoing monitoring proportionate to criticality.",6,"High"),
    ("us","SEC","17 CFR 229.106","Cybersecurity risk management, strategy and governance disclosure","Rule","Regulatory reporting","2023-12-18","A registrant must describe its processes for assessing, identifying and managing material risks from cybersecurity threats, and must disclose board oversight and management expertise in annual reports.",4,"High"),
    ("us","FTC","16 CFR 314.4","Safeguards Rule: elements of an information security programme","Rule","Cyber security","2023-06-09","A financial institution shall designate a qualified individual to oversee its information security programme, conduct written risk assessments, implement access controls and encryption, and report to the board at least annually.",6,"High"),
    ("us","HHS","45 CFR 164.308","HIPAA administrative safeguards","Regulation","Data privacy","2013-03-26","A covered entity must implement policies and procedures to prevent, detect, contain and correct security violations, including risk analysis, workforce sanctions, and periodic evaluation of security measures.",5,"High"),
    ("ca","FINTRAC","PCMLTFA s.9.6","Compliance programme requirement","Act / Statute","AML / CFT","2024-10-11","Every reporting entity shall implement a compliance programme that includes the appointment of a compliance officer, written policies and procedures, a risk assessment, ongoing training and a biennial effectiveness review.",5,"High"),
    ("ca","FINTRAC","PCMLTFR s.105","Suspicious transaction reporting timing","Regulation","AML / CFT","2024-10-11","A reporting entity shall send a suspicious transaction report as soon as practicable after it has taken measures that enable it to establish there are reasonable grounds to suspect a transaction is related to money laundering.",3,"Critical"),
    ("ca","OSFI","Guideline B-10","Third-party risk management","Guideline","Outsourcing and third party","2024-05-01","A federally regulated financial institution should maintain a third-party risk management framework with a centralised record of arrangements, risk-based due diligence, contractual rights to audit, and exit and transition plans for critical arrangements.",7,"High"),
    ("ca","OSFI","Guideline B-13","Technology and cyber risk management","Guideline","Cyber security","2024-01-01","An institution should maintain a technology and cyber risk management framework covering governance, risk management, technology operations, cyber security, and third-party provider oversight, with reporting to senior management.",8,"High"),
    ("ca","OSFI","Guideline E-21","Operational resilience and operational risk management","Guideline","Operational resilience","2026-09-01","An institution should identify critical operations, set tolerances for disruption, conduct scenario testing against severe but plausible scenarios, and maintain a resilience framework approved by senior management.",6,"High"),
    ("ca","FCAC","Bank Act s.627","Complaint handling procedures for banks","Act / Statute","Complaints handling","2022-06-30","A bank shall establish procedures for dealing with complaints, designate an officer responsible, deal with a complaint within 56 days of receipt, and inform the complainant of the external complaints body.",4,"Medium"),
    ("uk","FCA","SYSC 6.3","Financial crime systems and controls","Rule","AML / CFT","2023-07-31","A firm must ensure that its systems and controls enable it to identify, assess, monitor and manage money laundering risk, and that they are comprehensive and proportionate to the nature, scale and complexity of its activities.",5,"High"),
    ("uk","HM Treasury","MLR 2017 reg.28","Customer due diligence measures","Regulation","KYC and CDD","2023-09-01","A relevant person must identify the customer and verify their identity on the basis of documents or information obtained from a reliable source, and where there is a beneficial owner, take reasonable measures to verify their identity.",6,"High"),
    ("uk","FCA","PRIN 2A","Consumer Duty: acting to deliver good outcomes for retail customers","Rule","Consumer protection","2023-07-31","A firm must act to deliver good outcomes for retail customers across products and services, price and value, consumer understanding and consumer support, and must monitor and evidence outcomes on an ongoing basis.",8,"Critical"),
    ("uk","FCA","SYSC 15A","Operational resilience: important business services","Rule","Operational resilience","2025-03-31","A firm must identify its important business services, set impact tolerances for each, carry out mapping and scenario testing, and remain within impact tolerance for each important business service in the event of a severe but plausible disruption.",7,"Critical"),
    ("uk","FCA","SYSC 8.1","Outsourcing and critical third parties","Rule","Outsourcing and third party","2024-01-01","A firm must exercise due skill, care and diligence when entering into, managing or terminating an outsourcing arrangement, and must ensure the arrangement does not impair the quality of its internal control.",5,"High"),
    ("uk","PRA","PRA Rulebook: Reporting","COREP and FINREP regulatory returns","Rule","Regulatory reporting","2024-01-01","A firm must submit prudential returns covering own funds, liquidity and large exposures at the frequency and within the remittance dates set out in the reporting rules, and must have adequate controls over data quality.",5,"Medium"),
    ("uk","ICO","UK GDPR Art.32","Security of processing","Regulation","Cyber security","2021-01-01","The controller and processor shall implement appropriate technical and organisational measures to ensure a level of security appropriate to the risk, including pseudonymisation and encryption, and a process for regularly testing effectiveness.",5,"High"),
    ("uk","ICO","UK GDPR Art.33","Notification of a personal data breach to the regulator","Regulation","Data privacy","2021-01-01","In the case of a personal data breach, the controller shall without undue delay and, where feasible, not later than 72 hours after having become aware of it, notify the supervisory authority unless the breach is unlikely to result in a risk.",4,"Critical"),
    ("uk","FCA","SYSC 25","Senior management responsibilities and accountability","Rule","Governance and accountability","2023-03-01","A firm must allocate prescribed responsibilities to senior managers, maintain responsibilities maps and statements of responsibility, and certify annually that certified staff remain fit and proper.",6,"High"),
    ("eu","EDPB","GDPR Art.30","Records of processing activities","Regulation","Data privacy","2018-05-25","Each controller shall maintain a record of processing activities under its responsibility containing the purposes of processing, categories of data subjects and personal data, recipients, transfers and retention periods.",4,"Medium"),
    ("eu","EDPB","GDPR Art.35","Data protection impact assessment","Regulation","Data privacy","2018-05-25","Where processing is likely to result in a high risk to the rights and freedoms of natural persons, the controller shall, prior to processing, carry out an assessment of the impact of the envisaged processing operations.",5,"High"),
    ("eu","EBA","DORA Art.5","ICT risk management framework and governance","Regulation","Operational resilience","2025-01-17","Financial entities shall have in place an internal governance and control framework that ensures effective and prudent management of ICT risk, with the management body bearing ultimate responsibility and approving the ICT strategy.",7,"Critical"),
    ("eu","EBA","DORA Art.19","Reporting of major ICT-related incidents","Regulation","Operational resilience","2025-01-17","Financial entities shall report major ICT-related incidents to the competent authority using harmonised templates, submitting an initial notification, an intermediate report and a final report within the prescribed deadlines.",4,"Critical"),
    ("eu","EBA","CRR Art.92","Own funds requirements and capital ratios","Regulation","Capital and liquidity","2025-01-01","Institutions shall at all times satisfy a common equity tier 1 capital ratio of 4.5 percent, a tier 1 capital ratio of 6 percent and a total capital ratio of 8 percent of the total risk exposure amount.",4,"High"),
    ("eu","ECB","PSD2 Art.97","Strong customer authentication for electronic payments","Directive","Fraud and payments","2019-09-14","A payment service provider shall apply strong customer authentication where the payer accesses a payment account online, initiates an electronic payment transaction or carries out any action through a remote channel implying risk of fraud.",5,"High"),
    ("in","RBI","Master Direction DBR.AML.BC.81","Know Your Customer (KYC) Direction","Master Direction","KYC and CDD","2025-01-06","Regulated entities shall undertake customer due diligence while commencing an account-based relationship, obtain officially valid documents, carry out risk categorisation of customers and conduct periodic updation of KYC records.",8,"High"),
    ("in","RBI","DPSS.CO.PD.No.1810","Storage of payment system data","Circular","Data localisation","2018-04-06","All system providers shall ensure that the entire data relating to payment systems operated by them is stored in a system only in India, and shall submit a system audit report conducted by a CERT-In empanelled auditor.",4,"Critical"),
    ("in","RBI","CO.CSITE.SEC.1852","Master Direction on Information Technology Governance, Risk and Controls","Master Direction","Cyber security","2024-04-01","Regulated entities shall put in place a board-approved IT strategy and policy, constitute an IT strategy committee, maintain an information security policy and conduct periodic vulnerability assessment and penetration testing.",9,"High"),
    ("in","RBI","DOS.CO.CSITEG/SEC.7","Master Direction on Outsourcing of Information Technology Services","Master Direction","Outsourcing and third party","2023-04-10","Regulated entities shall not outsource core management functions, shall conduct due diligence on service providers, include audit and inspection rights in agreements, and maintain exit strategies for material outsourcing.",7,"High"),
    ("in","RBI","CEPD.PRS.No.S874","Internal Ombudsman and complaint redressal","Circular","Complaints handling","2023-12-28","Regulated entities shall appoint an Internal Ombudsman to examine complaints that are partly or wholly rejected, and shall display the grievance redressal mechanism prominently at branches and on the website.",4,"Medium"),
    ("in","SEBI","SEBI CSCRF 2024","Cyber security and cyber resilience framework for regulated entities","Circular","Cyber security","2025-04-01","Regulated entities shall adopt the cyber security and cyber resilience framework covering governance, identification of critical assets, protection, detection, response and recovery, with periodic reporting to the board.",8,"High"),
    ("in","MeitY","DPDP Act s.8","Obligations of a data fiduciary","Act / Statute","Data privacy","2025-11-01","A data fiduciary shall implement appropriate technical and organisational measures, protect personal data in its possession, and intimate each affected data principal and the Board in the event of a personal data breach.",6,"Critical"),
    ("in","RBI","DoR.FIN.REC.95","Fair practices code for lenders and digital lending","Circular","Consumer protection","2025-05-08","Regulated entities shall provide a key fact statement to the borrower before execution of the contract, disclose the all-inclusive annual percentage rate, and ensure recovery practices do not involve harassment.",5,"High"),
    ("cn","PBoC","PBoC Order No.3 (2022)","Anti-money laundering obligations of financial institutions","Regulation","AML / CFT","2022-03-01","Financial institutions shall establish customer identity identification systems, preserve customer identity materials and transaction records, and report large-value and suspicious transactions to the anti-money laundering authority.",6,"High"),
    ("cn","CAC","PIPL Art.38","Cross-border transfer of personal information","Act / Statute","Data localisation","2021-11-01","Where a personal information handler provides personal information outside the territory, it shall pass a security assessment organised by the state authority, obtain certification, or conclude standard contractual clauses.",5,"Critical"),
    ("cn","CAC","DSL Art.21","Classified protection of important data","Act / Statute","Data localisation","2021-09-01","The state shall establish a classified and categorised data protection system; processors of important data shall designate a person responsible, conduct periodic risk assessments and report assessment results to the authorities.",4,"High"),
    ("cn","NFRA","Commercial Bank Capital Rules 2024","Capital adequacy management for commercial banks","Regulation","Capital and liquidity","2024-01-01","Commercial banks shall classify risk exposures under the prescribed tiers, maintain minimum capital adequacy ratios, and submit capital adequacy reports to the regulator on a quarterly basis.",5,"High"),
    ("cn","PBoC","Circular 2023 No.147","Outsourcing risk management of information technology","Circular","Outsourcing and third party","2023-12-01","Financial institutions shall assess the concentration risk of information technology outsourcing, retain ultimate responsibility for outsourced activities, and report material outsourcing arrangements to the regulator.",4,"Medium"),
    ("jp","JFSA","AML/CFT Guidelines (rev. 2024)","Risk-based approach to money laundering and terrorist financing","Guideline","AML / CFT","2024-03-29","Financial institutions shall identify and assess money laundering risks across products, services, geographies and channels, apply risk-mitigating measures proportionate to assessed risk, and report the assessment to management.",6,"High"),
    ("jp","JFSA","FIEA Art.40","Conduct of business rules for financial instruments business operators","Act / Statute","Conduct and culture","2024-04-01","A financial instruments business operator shall establish a system to ensure suitability of solicitation having regard to the knowledge, experience, financial position and investment purpose of the customer.",5,"High"),
    ("jp","PPC","APPI Art.26","Reporting of personal data leakage","Act / Statute","Data privacy","2022-04-01","A personal information handling business operator shall report a leakage of personal data likely to harm the rights and interests of individuals to the Commission promptly, and notify the affected individuals.",4,"Critical"),
    ("jp","JFSA","Supervisory Guidelines III-2","System risk management and operational continuity","Supervisory expectation","Operational resilience","2024-06-01","Financial institutions should develop contingency plans for system failures, conduct regular drills including joint drills with external providers, and report material system failures to the authority without delay.",5,"High"),
    ("hk","HKMA","AMLO Sch.2 s.2","Customer due diligence requirements","Act / Statute","KYC and CDD","2023-06-01","A financial institution shall identify the customer and verify the customer identity, identify any beneficial owner and take reasonable measures to verify the beneficial owner identity, before establishing a business relationship.",6,"High"),
    ("hk","HKMA","AML/CFT Guideline Ch.4","Risk-based approach and ongoing monitoring","Guideline","AML / CFT","2024-09-30","An authorised institution should continuously monitor its business relationship with a customer, review existing records to ensure documents and information remain up to date and relevant, and scrutinise complex or unusually large transactions.",7,"High"),
    ("hk","HKMA","SPM Module OR-2","Operational resilience and operational risk management","Supervisory expectation","Operational resilience","2026-05-31","An authorised institution should become operationally resilient by May 2026, identifying critical operations, setting tolerance for disruption, and conducting severe but plausible scenario testing with board oversight.",7,"Critical"),
    ("hk","HKMA","SPM Module SA-2","Outsourcing of activities by authorised institutions","Supervisory expectation","Outsourcing and third party","2024-02-01","An authorised institution should consult the regulator before entering into a material outsourcing arrangement, retain the ability to meet supervisory requirements, and ensure customer data confidentiality is maintained.",5,"High"),
    ("hk","PCPD","PDPO DPP4","Security of personal data","Act / Statute","Data privacy","2021-10-08","All practicable steps shall be taken to ensure that personal data held by a data user is protected against unauthorised or accidental access, processing, erasure, loss or use, having regard to the harm that could result.",4,"High"),
    ("hk","SFC","Code of Conduct para 4.3","Internal controls and management responsibility","Code of practice","Governance and accountability","2023-10-01","A licensed person should have internal control procedures and financial and operational capabilities which can reasonably be expected to protect its operations and its clients from financial loss arising from theft, fraud or other dishonest acts.",5,"High"),
    ("kr","FSC","EFTA Art.21","Safety and security of electronic financial transactions","Act / Statute","Cyber security","2024-01-01","A financial company shall comply with the standards for human resources, facilities, electronic devices and procedures necessary to ensure the safety and reliability of electronic financial transactions.",5,"High"),
    ("kr","PIPC","PIPA Art.29","Duty of safety measures for personal information","Act / Statute","Data privacy","2024-03-15","A personal information controller shall take technical, administrative and physical measures necessary to secure safety, including establishing an internal management plan and keeping access records, to prevent loss or leakage.",5,"High"),
    ("kr","FSS","AML Supervisory Regulation Art.22","Suspicious transaction and currency transaction reporting","Regulation","AML / CFT","2023-07-01","A financial company shall report suspicious transactions to the Korea Financial Intelligence Unit without delay, and report currency transactions exceeding the prescribed threshold within the statutory period.",4,"High"),
    ("sg","MAS","MAS Notice 626","Prevention of money laundering and countering the financing of terrorism for banks","Notice","AML / CFT","2024-07-01","A bank shall perform customer due diligence measures when establishing business relations, conduct enhanced due diligence on higher risk customers including politically exposed persons, and screen against relevant sanctions lists.",7,"High"),
    ("sg","MAS","MAS Notice 655","Cyber hygiene requirements","Notice","Cyber security","2022-08-06","A relevant entity shall ensure administrative accounts are secured, security patches are applied in a timely manner, a baseline standard is implemented, networks are secured, malware protection is deployed and multi-factor authentication is enforced.",6,"High"),
    ("sg","MAS","Outsourcing Guidelines 2024","Risk management practices for outsourcing arrangements","Guideline","Outsourcing and third party","2024-12-05","An institution should maintain a register of all outsourcing arrangements, conduct due diligence and risk evaluation before outsourcing, and ensure the regulator has the right to access and inspect the service provider.",6,"High"),
    ("sa","SAMA","SAMA CSF 3.3","Cyber security governance and risk management","Standard","Cyber security","2024-02-01","A member organisation shall define, approve and implement a cyber security governance structure, appoint a cyber security function independent of IT, and conduct periodic cyber security risk assessments reported to the board.",8,"High"),
    ("sa","SAMA","SAMA AML Rules 2023","Anti-money laundering and counter-terrorist financing rules","Rule","AML / CFT","2023-05-01","A financial institution shall apply customer due diligence measures, maintain records for at least ten years, appoint a compliance officer at management level and report suspicious transactions to the Financial Intelligence Unit.",6,"High"),
    ("sa","SAMA","Business Continuity Framework 2023","Business continuity management requirements","Standard","Operational resilience","2023-09-01","A member organisation shall maintain a business continuity management programme including business impact analysis, recovery time objectives for critical services, and annual testing of continuity and disaster recovery plans.",5,"Medium"),
    ("af","SARB","Directive 1 of 2024","Risk management and internal controls for banks","Directive","Governance and accountability","2024-03-01","A bank shall maintain a governance framework in which the board approves risk appetite, the risk and compliance functions have unrestricted access to the board, and internal audit independently assesses control effectiveness.",6,"High"),
    ("af","FIC","FIC Act s.42","Risk management and compliance programme","Act / Statute","AML / CFT","2023-04-01","An accountable institution must develop, document, maintain and implement a risk management and compliance programme setting out how it identifies, assesses, monitors, mitigates and manages money laundering risk.",5,"High"),
    ("af","CBN","CBN Consumer Protection Regulations","Responsible business conduct and disclosure","Regulation","Consumer protection","2023-01-01","A financial institution shall disclose all fees, charges and interest in a key facts statement before onboarding, resolve customer complaints within the prescribed timeline and maintain a complaints register.",4,"Medium"),
    ("af","Information Regulator","POPIA s.19","Security measures on integrity and confidentiality of personal information","Act / Statute","Data privacy","2021-07-01","A responsible party must secure the integrity and confidentiality of personal information in its possession by taking appropriate, reasonable technical and organisational measures to prevent loss, damage or unauthorised access.",4,"High"),
]

JN = {j["id"]: j["name"] for j in JURISDICTIONS}
rules = []
for i, (j, reg, cite, title, rtype, matter, date, text, obl, sev) in enumerate(R, start=101):
    rules.append({
        "id": f"RUL-{i}", "juris": j, "jurisName": JN[j], "regulator": reg, "cite": cite,
        "title": title, "ruleType": rtype, "ruleMatter": matter, "effectiveDate": date,
        "text": text, "severity": sev, "obligationCount": obl,
        "frameworks": FW_TAGS.get(matter, []),
        "detailKey": "reg-b-1002-12" if cite == "12 CFR 1002.12" else None,
    })

CONTROLS = [
    ("CTRL-01","Identity verification at onboarding","Onboarding Ops","Preventive","Automated",["us","uk","in","hk","sg"],"KYC and CDD","Effective"),
    ("CTRL-02","Beneficial ownership capture and verification","KYC Utility","Preventive","Semi-automated",["us","uk","hk"],"KYC and CDD","Needs improvement"),
    ("CTRL-03","Periodic KYC refresh by risk tier","KYC Utility","Detective","Automated",["in","hk","sg"],"KYC and CDD","Effective"),
    ("CTRL-04","Transaction monitoring scenario library","FCC Analytics","Detective","Automated",["us","uk","hk","sg","ca"],"AML / CFT","Effective"),
    ("CTRL-05","Suspicious activity report filing workflow","FCC Investigations","Corrective","Semi-automated",["us","ca","kr","af"],"AML / CFT","Effective"),
    ("CTRL-06","Sanctions list screening at payment initiation","Payments Ops","Preventive","Automated",["us","uk","eu","sg"],"Sanctions screening","Effective"),
    ("CTRL-07","Blocked property reporting register","Sanctions Office","Detective","Manual",["us"],"Sanctions screening","Not tested"),
    ("CTRL-08","Strong customer authentication on remote channels","Digital Channels","Preventive","Automated",["eu","uk","in"],"Fraud and payments","Effective"),
    ("CTRL-09","Complaint intake, triage and SLA tracking","Customer Care","Detective","Automated",["ca","in","uk","af"],"Complaints handling","Needs improvement"),
    ("CTRL-10","Key facts statement generation and disclosure log","Product Governance","Preventive","Semi-automated",["us","in","af"],"Consumer protection","Effective"),
    ("CTRL-11","Fair value and outcomes monitoring dashboard","Product Governance","Detective","Automated",["uk"],"Consumer protection","Needs improvement"),
    ("CTRL-12","Third-party due diligence and risk tiering","Vendor Management","Preventive","Semi-automated",["us","ca","uk","in","hk","sg"],"Outsourcing and third party","Effective"),
    ("CTRL-13","Critical vendor exit and transition plan","Vendor Management","Corrective","Manual",["ca","uk","in","hk"],"Outsourcing and third party","Not tested"),
    ("CTRL-14","Outsourcing register with regulator notification flags","Vendor Management","Detective","Automated",["sg","hk","cn"],"Outsourcing and third party","Effective"),
    ("CTRL-15","Important business service mapping and impact tolerance","Resilience Office","Preventive","Semi-automated",["uk","hk","ca"],"Operational resilience","Needs improvement"),
    ("CTRL-16","Severe but plausible scenario testing programme","Resilience Office","Detective","Manual",["uk","hk","ca","sa"],"Operational resilience","Not tested"),
    ("CTRL-17","Major ICT incident classification and regulator reporting","Incident Command","Corrective","Semi-automated",["eu","jp"],"Operational resilience","Needs improvement"),
    ("CTRL-18","Vulnerability assessment and penetration testing cycle","Security Engineering","Detective","Automated",["in","sg","sa","kr"],"Cyber security","Effective"),
    ("CTRL-19","Privileged access management and access recertification","IAM Team","Preventive","Automated",["us","in","sg","sa","kr"],"Cyber security","Effective"),
    ("CTRL-20","Encryption of data at rest and in transit","Security Engineering","Preventive","Automated",["us","uk","eu","in","hk","af"],"Cyber security","Effective"),
    ("CTRL-21","Personal data breach assessment and 72-hour notification","Privacy Office","Corrective","Semi-automated",["uk","eu","in","jp","kr"],"Data privacy","Needs improvement"),
    ("CTRL-22","Records of processing activities maintenance","Privacy Office","Detective","Manual",["eu","uk"],"Data privacy","Effective"),
    ("CTRL-23","Data protection impact assessment gate","Privacy Office","Preventive","Semi-automated",["eu","uk","in"],"Data privacy","Effective"),
    ("CTRL-24","In-country data residency enforcement for payment data","Platform Engineering","Preventive","Automated",["in"],"Data localisation","Needs improvement"),
    ("CTRL-25","Cross-border transfer assessment and approval","Privacy Office","Preventive","Manual",["cn","kr","eu"],"Data localisation","Not tested"),
    ("CTRL-26","Regulatory return preparation and four-eye review","Regulatory Reporting","Detective","Semi-automated",["uk","eu","cn"],"Regulatory reporting","Effective"),
    ("CTRL-27","Capital adequacy calculation and attestation","Treasury","Preventive","Automated",["eu","cn"],"Capital and liquidity","Effective"),
    ("CTRL-28","Senior manager responsibility mapping and attestation","Governance Office","Preventive","Manual",["uk","us","af","hk"],"Governance and accountability","Effective"),
    ("CTRL-29","Board risk reporting pack with control effectiveness","Governance Office","Detective","Semi-automated",["us","af","sa","in"],"Governance and accountability","Effective"),
    ("CTRL-30","Suitability assessment at point of sale","Advisory Supervision","Preventive","Semi-automated",["jp","hk"],"Conduct and culture","Needs improvement"),
    ("CTRL-31","Record retention schedule enforcement","Information Governance","Preventive","Automated",["us","uk","sa","cn"],"Records and retention","Effective"),
    ("CTRL-32","Credit application file retention for 25 months","Information Governance","Detective","Semi-automated",["us"],"Records and retention","Needs improvement"),
]
controls = [{"id": c[0], "name": c[1], "owner": c[2], "controlType": c[3], "automation": c[4],
             "jurisdictions": c[5], "ruleMatter": c[6], "testResult": c[7]} for c in CONTROLS]

POLICIES = [
    ("POL-01","Group Anti-Money Laundering Policy","Group Head of FCC","v6.2","2026-03-31",["us","uk","ca","hk","sg","in"],"AML / CFT"),
    ("POL-02","Know Your Customer and CDD Standard","Head of Onboarding","v4.0","2026-01-31",["us","uk","hk","in","sg"],"KYC and CDD"),
    ("POL-03","Sanctions Compliance Policy","Head of Sanctions","v3.1","2026-06-30",["us","uk","eu","sg"],"Sanctions screening"),
    ("POL-04","Consumer Outcomes and Fair Treatment Policy","Head of Conduct","v2.4","2026-04-30",["uk","us","in","af"],"Consumer protection"),
    ("POL-05","Third Party and Outsourcing Risk Policy","Chief Procurement Officer","v5.0","2026-02-28",["us","ca","uk","in","hk","sg","cn"],"Outsourcing and third party"),
    ("POL-06","Operational Resilience Policy","Chief Operating Officer","v1.3","2026-05-31",["uk","hk","ca","eu","sa"],"Operational resilience"),
    ("POL-07","Information Security Policy","Chief Information Security Officer","v8.1","2026-01-15",["us","uk","eu","in","sg","sa","kr"],"Cyber security"),
    ("POL-08","Global Privacy and Data Protection Policy","Group Data Protection Officer","v4.5","2026-03-15",["uk","eu","in","jp","kr","hk","af"],"Data privacy"),
    ("POL-09","Data Residency and Cross-Border Transfer Standard","Group DPO","v2.0","2026-07-31",["in","cn","kr","eu"],"Data localisation"),
    ("POL-10","Regulatory Reporting Policy","Group Financial Controller","v3.3","2026-02-15",["uk","eu","cn"],"Regulatory reporting"),
    ("POL-11","Capital Management Policy","Group Treasurer","v4.1","2026-06-15",["eu","cn"],"Capital and liquidity"),
    ("POL-12","Complaints Management Policy","Head of Customer Care","v2.2","2026-04-15",["ca","in","uk","af"],"Complaints handling"),
    ("POL-13","Risk Governance and Accountability Framework","Chief Risk Officer","v7.0","2026-01-31",["us","uk","af","sa","hk","in"],"Governance and accountability"),
    ("POL-14","Fraud and Payment Security Policy","Head of Fraud Risk","v3.0","2026-05-15",["eu","uk","in"],"Fraud and payments"),
    ("POL-15","Records Management and Retention Policy","Chief Data Officer","v2.8","2026-08-31",["us","uk","sa","cn"],"Records and retention"),
    ("POL-16","Sales Conduct and Suitability Policy","Head of Advisory","v1.9","2026-03-31",["jp","hk"],"Conduct and culture"),
]
policies = [{"id": p[0], "name": p[1], "owner": p[2], "version": p[3], "nextReview": p[4],
             "jurisdictions": p[5], "ruleMatter": p[6]} for p in POLICIES]

RISKS = [
    ("RSK-01","Onboarding a customer without verified beneficial owner","KYC and CDD","High","Medium","Low"),
    ("RSK-02","Failure to detect and report suspicious activity in time","AML / CFT","Critical","High","Low"),
    ("RSK-03","Sanctioned party payment released","Sanctions screening","Critical","Medium","Zero"),
    ("RSK-04","Poor customer outcomes from product value mismatch","Consumer protection","High","High","Low"),
    ("RSK-05","Critical service disruption beyond impact tolerance","Operational resilience","Critical","High","Low"),
    ("RSK-06","Concentration risk in a single critical cloud provider","Outsourcing and third party","High","High","Medium"),
    ("RSK-07","Personal data breach not notified within statutory deadline","Data privacy","High","Medium","Low"),
    ("RSK-08","Payment data stored outside the permitted territory","Data localisation","Critical","High","Zero"),
    ("RSK-09","Unauthorised privileged access to core systems","Cyber security","Critical","Medium","Low"),
    ("RSK-10","Inaccurate or late regulatory return","Regulatory reporting","Medium","Low","Low"),
    ("RSK-11","Unresolved complaints breaching statutory timelines","Complaints handling","Medium","Medium","Low"),
    ("RSK-12","Accountability gaps in senior manager responsibilities","Governance and accountability","High","Low","Low"),
    ("RSK-13","Credit application records destroyed before the retention period ends","Records and retention","High","Medium","Low"),
]
risks = [{"id": r[0], "name": r[1], "ruleMatter": r[2], "inherent": r[3], "residual": r[4], "appetite": r[5]} for r in RISKS]

ISSUES = [
    ("ISS-01","RSK-01","Beneficial ownership evidence missing for 312 legacy entity accounts","High","KYC Utility","2026-01-30","In progress"),
    ("ISS-02","RSK-05","Scenario testing not performed for two important business services","High","Resilience Office","2026-02-28","Open"),
    ("ISS-03","RSK-08","Payment tokens replicated to a non-Indian disaster recovery region","Critical","Platform Engineering","2025-12-15","Open"),
    ("ISS-04","RSK-06","No tested exit plan for the core cloud hosting arrangement","High","Vendor Management","2026-03-31","Open"),
    ("ISS-05","RSK-07","Breach assessment workflow cannot evidence the 72-hour clock","Medium","Privacy Office","2026-02-15","In progress"),
    ("ISS-06","RSK-04","Fair value assessments outstanding for 9 retail products","High","Product Governance","2026-04-30","In progress"),
    ("ISS-07","RSK-03","Manual blocked-property register has no maker-checker control","Medium","Sanctions Office","2026-03-15","Open"),
    ("ISS-08","RSK-11","Internal Ombudsman escalations tracked outside the case system","Medium","Customer Care","2026-05-31","Open"),
    ("ISS-09","RSK-02","Alert backlog exceeds the 30-day SAR filing clock in two markets","Critical","FCC Investigations","2026-01-15","In progress"),
    ("ISS-10","RSK-09","Privileged access recertification overdue for four core platforms","High","IAM Team","2026-02-20","Open"),
    ("ISS-11","RSK-13","Regulation B application files purged at 18 months in two branches","High","Information Governance","2026-03-20","Open"),
]
issues = [{"id": i[0], "riskId": i[1], "name": i[2], "severity": i[3], "owner": i[4], "due": i[5], "status": i[6]} for i in ISSUES]

CHANGES = [
    {
        "id": "CHG-01", "juris": "hk", "regulator": "HKMA",
        "title": "AML/CFT Guideline amended: ongoing monitoring and PEP scope",
        "published": "2026-11-04", "effective": "2027-02-01", "status": "Impact analysis",
        "impact": "High", "affectedCites": ["AML/CFT Guideline Ch.4"],
        "summary": "Chapter 4 is amended to require continuous rather than periodic monitoring for higher-risk relationships, and widens the definition of a politically exposed person to include domestic PEPs and their close associates.",
        "diff": [
            {"kind": "unchanged", "text": "An authorised institution should continuously monitor its business relationship with a customer,"},
            {"kind": "removed", "text": "review existing records periodically to ensure documents remain up to date"},
            {"kind": "added", "text": "review existing records on a continuous and event-driven basis to ensure documents, data and information remain up to date and relevant"},
            {"kind": "unchanged", "text": "and scrutinise complex or unusually large transactions."},
            {"kind": "added", "text": "For the purposes of this Chapter, a politically exposed person includes a domestic politically exposed person and their close associates."},
        ],
    },
    {
        "id": "CHG-02", "juris": "in", "regulator": "RBI",
        "title": "Draft direction on digital lending partnerships",
        "published": "2026-11-02", "effective": "2027-04-01", "status": "Triaged",
        "impact": "Medium", "affectedCites": ["DoR.FIN.REC.95"],
        "summary": "Extends the key fact statement requirement to loans sourced through lending service providers and requires the all-inclusive annual percentage rate to be shown before the borrower consents.",
        "diff": [
            {"kind": "unchanged", "text": "Regulated entities shall provide a key fact statement to the borrower before execution of the contract,"},
            {"kind": "added", "text": "including where the loan is sourced or serviced through a lending service provider,"},
            {"kind": "unchanged", "text": "disclose the all-inclusive annual percentage rate,"},
        ],
    },
    {
        "id": "CHG-03", "juris": "eu", "regulator": "EBA",
        "title": "DORA incident reporting templates finalised",
        "published": "2026-10-28", "effective": "2027-01-17", "status": "Assigned",
        "impact": "High", "affectedCites": ["DORA Art.19"],
        "summary": "The harmonised templates are final. The intermediate report window shortens from 72 to 48 hours and a new field set is required for third-party-originated incidents.",
        "diff": [
            {"kind": "unchanged", "text": "Financial entities shall report major ICT-related incidents to the competent authority using harmonised templates,"},
            {"kind": "removed", "text": "submitting an intermediate report within 72 hours"},
            {"kind": "added", "text": "submitting an intermediate report within 48 hours, and identifying whether the incident originated with a third-party provider"},
        ],
    },
    {
        "id": "CHG-04", "juris": "uk", "regulator": "FCA",
        "title": "Consumer Duty board report expectations clarified",
        "published": "2026-10-21", "effective": "2027-07-31", "status": "New",
        "impact": "Medium", "affectedCites": ["PRIN 2A"],
        "summary": "The annual board report must now evidence outcomes for customers in vulnerable circumstances separately, with supporting data.",
        "diff": [
            {"kind": "unchanged", "text": "A firm must act to deliver good outcomes for retail customers"},
            {"kind": "added", "text": "and must evidence, separately, outcomes for customers in vulnerable circumstances in its annual board report."},
        ],
    },
    {
        "id": "CHG-05", "juris": "us", "regulator": "CFPB",
        "title": "Regulation B record retention period under review",
        "published": "2026-10-09", "effective": "2027-06-30", "status": "New",
        "impact": "Medium", "affectedCites": ["12 CFR 1002.12"],
        "summary": "A proposal would extend the retention window for business-credit applications from 12 to 25 months, aligning it with consumer credit.",
        "diff": [
            {"kind": "unchanged", "text": "For 25 months"},
            {"kind": "removed", "text": "(12 months for business credit, except as provided in paragraph (b)(5) of this section)"},
            {"kind": "added", "text": "(25 months for business credit)"},
            {"kind": "unchanged", "text": "after the date that a creditor notifies an applicant of action taken on an application"},
        ],
    },
]

SEMANTIC = {
    "beneficial owner": ["ultimate beneficial owner", "ubo", "ownership structure", "control person", "legal entity customer"],
    "customer due diligence": ["cdd", "kyc", "identity verification", "onboarding checks", "officially valid document"],
    "suspicious": ["suspicious activity report", "sar", "str", "unusual transaction", "red flag"],
    "sanctions": ["screening", "blocked property", "ofac", "watchlist", "designated person"],
    "outsourcing": ["third party", "service provider", "vendor", "material arrangement", "exit plan"],
    "resilience": ["important business service", "impact tolerance", "scenario testing", "business continuity", "critical operation"],
    "privacy": ["personal data", "data subject", "breach notification", "processing record", "dpia"],
    "localisation": ["data residency", "cross-border transfer", "in-country storage", "security assessment"],
    "cyber": ["information security", "vapt", "encryption", "privileged access", "patching"],
    "complaint": ["grievance", "redressal", "ombudsman", "dispute resolution"],
    "capital": ["own funds", "cet1", "capital adequacy", "risk exposure amount"],
    "authentication": ["strong customer authentication", "multi-factor", "sca", "remote channel"],
    "governance": ["board oversight", "senior manager", "accountability", "responsibilities map", "risk appetite"],
    "retention": ["record keeping", "retention period", "preserve records", "archive", "25 months"],
}

for name, payload in [
    ("jurisdictions", JURISDICTIONS), ("frameworks", FRAMEWORKS), ("rules", rules),
    ("controls", controls), ("policies", policies), ("risks", risks), ("issues", issues),
    ("changes", CHANGES), ("semantic", SEMANTIC),
    ("taxonomy", {"ruleMatters": RULE_MATTERS, "ruleTypes": RULE_TYPES}),
]:
    (SEED / f"{name}.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  {name}.json  ({len(payload)} entries)")
print("seed written to", SEED)
