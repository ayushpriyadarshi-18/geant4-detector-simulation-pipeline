#pragma once

#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4GenericMessenger.hh"
#include "G4SystemOfUnits.hh"

class G4GeneralParticleSource;
class G4Event;
class DetectorConstruction;

class PrimaryGeneratorAction : public G4VUserPrimaryGeneratorAction
{
public:
  PrimaryGeneratorAction();
  ~PrimaryGeneratorAction() override;

  void GeneratePrimaries(G4Event* event) override;

private:
  G4GeneralParticleSource* fGPS = nullptr;
  G4GenericMessenger* fMessenger = nullptr;

  G4double fManualZ = 81.2 * mm;

  G4bool   fUsePlastic = false;
  G4double fDepth      = 1.0 * mm;
};