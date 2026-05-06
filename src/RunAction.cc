#include "RunAction.hh"

#include "G4AnalysisManager.hh"
#include "G4Run.hh"
#include "G4Threading.hh"

RunAction::RunAction() : G4UserRunAction()
{
  auto man = G4AnalysisManager::Instance();

  man->SetDefaultFileType("root");
  man->SetFileName("events");      // -> events.root
  man->SetNtupleMerging(false);     // IMPORTANT for MT

  // Create ntuple schema once per thread (constructor is safest)
  man->CreateNtuple("events", "per-event energy deposition");
  man->CreateNtupleDColumn("Edep_keV");
  man->CreateNtupleDColumn("EdepCrystal_keV");
  man->CreateNtupleDColumn("EdepAl_keV");
  man->CreateNtupleDColumn("CosTheta");
  man->CreateNtupleDColumn("Phi");
  man->FinishNtuple();
}

RunAction::~RunAction()
{
  // Do NOT delete the analysis manager manually in MT mode.
  // Let Geant4 handle cleanup; manual deletion can cause exit-time segfaults
  // and corrupted ROOT files when merging is enabled.
}

void RunAction::BeginOfRunAction(const G4Run*)
{
  auto man = G4AnalysisManager::Instance();
  man->OpenFile();
}

void RunAction::EndOfRunAction(const G4Run*)
{
  auto man = G4AnalysisManager::Instance();
  man->Write();
  man->CloseFile();
}