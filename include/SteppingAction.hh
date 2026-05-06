#ifndef SteppingAction_hh
#define SteppingAction_hh

#include "G4UserSteppingAction.hh"

class EventAction;
class G4Step;

class SteppingAction : public G4UserSteppingAction
{
public:
  explicit SteppingAction(EventAction* eventAction);
  ~SteppingAction() override;

  void UserSteppingAction(const G4Step* step) override;

private:
  EventAction* fEventAction = nullptr;
};

#endif