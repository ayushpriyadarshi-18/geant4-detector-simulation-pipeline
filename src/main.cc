#include "G4RunManagerFactory.hh"
#include "G4UImanager.hh"
#include "G4UIExecutive.hh"
#include "G4VisExecutive.hh"
#include "G4VisManager.hh"
#include "G4AnalysisManager.hh"

#include "G4PhysListFactory.hh"
#include "G4VModularPhysicsList.hh"
#include "G4OpticalPhysics.hh"
#include "G4RadioactiveDecayPhysics.hh"

// (Recommended) avoid the troublesome UI command by setting threshold in C++
#include "G4HadronicParameters.hh"
#include "G4SystemOfUnits.hh"

#include "DetectorConstruction.hh"
#include "ActionInitialization.hh"

int main(int argc, char** argv)
{
  // Interactive UI only if no macro is provided
  G4UIExecutive* ui = nullptr;
  if (argc == 1) {
    ui = new G4UIExecutive(argc, argv);
  }

  // IMPORTANT: allow long-lived nuclei (Co-60) to decay within event time
  G4HadronicParameters::Instance()->SetTimeThresholdForRadioactiveDecay(1.0e+60 * year);

  // Run manager (MT)
  auto* runManager = G4RunManagerFactory::CreateRunManager(G4RunManagerType::Serial);

  // (Debug option) if you want to force 1 thread to simplify:
  // runManager->SetNumberOfThreads(1);

  runManager->SetUserInitialization(new DetectorConstruction());

  // Physics list
  G4PhysListFactory physListFactory;
  auto* physicsList = physListFactory.GetReferencePhysList("FTFP_BERT");
  physicsList->RegisterPhysics(new G4OpticalPhysics());
  physicsList->RegisterPhysics(new G4RadioactiveDecayPhysics());
  runManager->SetUserInitialization(physicsList);

  // User actions
  runManager->SetUserInitialization(new ActionInitialization());

  // Visualization: ONLY in interactive mode
  G4VisManager* visManager = nullptr;
  if (ui) {
    visManager = new G4VisExecutive();
    visManager->Initialize();
  }

  auto* UImanager = G4UImanager::GetUIpointer();

  if (!ui) {
    // Batch mode: execute macro passed as argv[1]
    G4String command = "/control/execute ";
    UImanager->ApplyCommand(command + G4String(argv[1]));
  } else {
    // Interactive mode
    // UImanager->ApplyCommand("/control/execute macros/vis.mac");
    ui->SessionStart();
    delete ui;
  }

  if (visManager) delete visManager;
  delete runManager;
  delete G4AnalysisManager::Instance();
  return 0;
}