#include "PrimaryGeneratorAction.hh"

#include "DetectorConstruction.hh"

#include "G4Event.hh"
#include "G4GeneralParticleSource.hh"
#include "G4GenericMessenger.hh"
#include "G4RunManager.hh"
#include "G4SingleParticleSource.hh"
#include "G4SPSPosDistribution.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"

PrimaryGeneratorAction::PrimaryGeneratorAction()
{
  fGPS = new G4GeneralParticleSource();

  fMessenger = new G4GenericMessenger(this, "/src/", "Source control");

  fMessenger->DeclarePropertyWithUnit("manualZ", "mm", fManualZ,
    "Manual source Z position (mm).");

  fMessenger->DeclareProperty("usePlastic", fUsePlastic,
    "Place source inside plastic holder if true.");

  fMessenger->DeclarePropertyWithUnit("depth", "mm", fDepth,
    "Depth of source inside plastic measured from the front face of the plastic.");
}

PrimaryGeneratorAction::~PrimaryGeneratorAction()
{
  delete fMessenger;
  fMessenger = nullptr;

  delete fGPS;
  fGPS = nullptr;
}

void PrimaryGeneratorAction::GeneratePrimaries(G4Event* event)
{
  G4double sourceZ = fManualZ;

  if (fUsePlastic) {
    auto* dc = static_cast<const DetectorConstruction*>(
      G4RunManager::GetRunManager()->GetUserDetectorConstruction());

    if (dc && dc->GetUsePlastic()) {
      const G4double zPlastic = dc->GetPlasticZ();
      const G4double hPlastic = dc->GetPlasticHalfZ();

      // front face is at zPlastic - hPlastic
      // source sits depth mm inside from that face
      sourceZ = zPlastic - hPlastic + fDepth;
    }
  }

  auto* src = fGPS->GetCurrentSource();
  src->GetPosDist()->SetCentreCoords(G4ThreeVector(0., 0., sourceZ));

  fGPS->GeneratePrimaryVertex(event);
}