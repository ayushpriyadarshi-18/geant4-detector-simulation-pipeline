#ifndef EventAction_hh
#define EventAction_hh

#include "G4UserEventAction.hh"
#include "globals.hh"

class EventAction : public G4UserEventAction
{
public:
  EventAction();
  ~EventAction() override;

  void BeginOfEventAction(const G4Event*) override;
  void EndOfEventAction(const G4Event*) override;

  // Called from SteppingAction
  void AddEdepCrystal(G4double e) { fEdepCrystal += e; }
  void AddEdepAl(G4double e)      { fEdepAl      += e; }

private:
  G4double fEdepCrystal = 0.0;
  G4double fEdepAl      = 0.0;
};

#endif