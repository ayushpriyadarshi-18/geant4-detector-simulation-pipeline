#include "SteppingAction.hh"
#include "EventAction.hh"

#include "G4Step.hh"
#include "G4VPhysicalVolume.hh"
#include "G4String.hh"

SteppingAction::SteppingAction(EventAction* eventAction)
  : G4UserSteppingAction(),
    fEventAction(eventAction)
{
}

SteppingAction::~SteppingAction() = default;

void SteppingAction::UserSteppingAction(const G4Step* step)
{
  if (!fEventAction) return;

  const G4double edep = step->GetTotalEnergyDeposit();
  if (edep <= 0.) return;

  auto pv = step->GetPreStepPoint()->GetTouchableHandle()->GetVolume();
  if (!pv) return;

  const G4String pvName = pv->GetName();

  // Cylinder solid/hollow crystal volume
  if (pvName == "Crystal") {
    fEventAction->AddEdepCrystal(edep);
  }
  // Soccer-ball crystal modules
  else if (G4StrUtil::contains(pvName, "Soccer_")) {
    fEventAction->AddEdepCrystal(edep);
  }
  // Aluminium volumes for solid cylinder and soccer-ball envelopes
  else if (pvName == "AlDisk" ||
           pvName == "AlInnerLining" ||
           pvName == "AlOuterLining" ||
           G4StrUtil::contains(pvName, "AlInner_") ||
           G4StrUtil::contains(pvName, "AlSide_")) {
    fEventAction->AddEdepAl(edep);
  }
}
