#include "ActionInitialization.hh"

#include "PrimaryGeneratorAction.hh"
#include "EventAction.hh"
#include "RunAction.hh"
#include "SteppingAction.hh"

void ActionInitialization::BuildForMaster() const
{
  // MT master thread: do NOT set PrimaryGeneratorAction here
  SetUserAction(new RunAction());
}

void ActionInitialization::Build() const
{
  // Worker threads: primary generator MUST be set here
  SetUserAction(new PrimaryGeneratorAction());

  auto eventAction = new EventAction();
  SetUserAction(eventAction);

  auto runAction = new RunAction();
  SetUserAction(runAction);

  auto steppingAction = new SteppingAction(eventAction);
  SetUserAction(steppingAction);
}