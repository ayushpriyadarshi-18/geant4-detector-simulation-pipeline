#ifndef DetectorConstruction_hh
#define DetectorConstruction_hh

#include "G4VUserDetectorConstruction.hh"
#include "G4GenericMessenger.hh"
#include "globals.hh"
#include "G4SystemOfUnits.hh"

class G4LogicalVolume;
class G4VPhysicalVolume;

class DetectorConstruction : public G4VUserDetectorConstruction
{
  public:
    DetectorConstruction();
    ~DetectorConstruction() override;

    G4VPhysicalVolume* Construct() override;

    G4LogicalVolume* GetCrystalLV() const { return fLogicCrystal; }

    void SetCrystalRadius(G4double r);
    void SetCrystalHalfZ(G4double z);
    void SetCrystalMaterial(const G4String& name);
    void SetGeometryType(const G4String& type);
    void SetAlThickness(G4double t);

    void SetHollow(G4bool val);
    void SetInnerRadius(G4double r);
    void SetRadialThickness(G4double t);

    void SetUsePlastic(G4bool val);
    void SetPlasticZ(G4double z);

    G4bool GetUsePlastic() const { return fUsePlastic; }
    G4double GetPlasticZ() const { return fPlasticZ; }
    G4double GetPlasticHalfZ() const { return fPlasticHalfZ; }

  private:
    G4LogicalVolume* fLogicWorld   = nullptr;
    G4LogicalVolume* fLogicCrystal = nullptr;
    G4LogicalVolume* fLogicPlastic = nullptr;

    G4VPhysicalVolume* fPhysPlasticDisk = nullptr;

    G4GenericMessenger* fMessenger    = nullptr;
    G4GenericMessenger* fGeomMessenger = nullptr;

    G4double fCrystalRadius = 12.7 * mm;
    G4double fCrystalHalfZ  = 12.7 * mm;
    G4double fAlThickness   = 0.5 * mm;   // Used by solid Al disk and hollow Al linings. Soccer-ball Al remains unchanged.
    G4String fCrystalMaterialName = "NaI";
    G4String fGeometryType = "solid";  // solid, hollow, soccer

    G4bool   fIsHollow        = false;
    G4double fInnerRadius     = 0.0 * mm;
    G4double fRadialThickness = 0.0 * mm;

    G4bool   fUsePlastic   = false;
    G4double fPlasticZ     = 0.0 * mm;
    G4double fPlasticHalfZ = 2.5 * mm;   // 5 mm thick disk
};

#endif
