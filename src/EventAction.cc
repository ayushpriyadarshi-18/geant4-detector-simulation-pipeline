#include "EventAction.hh"

#include "G4AnalysisManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4Event.hh"
#include "G4PrimaryVertex.hh"
#include "G4PrimaryParticle.hh"
#include "G4PhysicalConstants.hh"   // twopi
#include <cmath>                    // std::atan2

EventAction::EventAction() : G4UserEventAction() {}
EventAction::~EventAction() {}

void EventAction::BeginOfEventAction(const G4Event*)
{
  fEdepCrystal = 0.0;
  fEdepAl      = 0.0;
}

void EventAction::EndOfEventAction(const G4Event* event)
{
  auto man = G4AnalysisManager::Instance();
  if (!man) return;

  const G4double total = fEdepCrystal + fEdepAl;

  // --- Get primary direction for isotropy checks ---
  G4double cosTheta = 0.0;
  G4double phi = 0.0;

  if (event && event->GetNumberOfPrimaryVertex() > 0) {
    auto vtx = event->GetPrimaryVertex(0);
    if (vtx && vtx->GetNumberOfParticle() > 0) {
      auto prim = vtx->GetPrimary(0);
      if (prim) {
        auto dir = prim->GetMomentumDirection(); // unit vector
        cosTheta = dir.z();
        phi = std::atan2(dir.y(), dir.x());      // [-pi, pi]
        if (phi < 0) phi += twopi;               // [0, 2pi)
      }
    }
  }

  // Fill columns in the SAME order they were created in RunAction.cc
  man->FillNtupleDColumn(0, total / keV);
  man->FillNtupleDColumn(1, fEdepCrystal / keV);
  man->FillNtupleDColumn(2, fEdepAl / keV);
  man->FillNtupleDColumn(3, cosTheta);
  man->FillNtupleDColumn(4, phi);

  man->AddNtupleRow();
}