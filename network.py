import torch.nn as nn
import torchvision


def l2n(x, eps=1e-6):
    return x / (torch.norm(x, p=2, dim=1, keepdim=True) + eps).expand_as(x)

class L2N(nn.Module):

    def __init__(self, eps=1e-6):
        super(L2N, self).__init__()
        self.eps = eps

    def forward(self, x):
        return l2n(x, eps=self.eps)

    def __repr__(self):
        return self.__class__.__name__ + '(' + 'eps=' + str(self.eps) + ')'


class Model(nn.Module):
    def __init__(self, args):
        super(Model, self).__init__()
        self.hash_bit = args.hash_bit
        self.base_model = getattr(torchvision.models, args.model_type)(pretrained=True)
        self.conv1 = self.base_model.conv1
        self.bn1 = self.base_model.bn1
        self.relu = self.base_model.relu
        self.maxpool = self.base_model.maxpool
        self.layer1 = self.base_model.layer1
        self.layer2 = self.base_model.layer2
        self.layer3 = self.base_model.layer3
        self.layer4 = self.base_model.layer4
        self.avgpool = self.base_model.avgpool
        self.feature_layers = nn.Sequential(self.conv1, self.bn1, self.relu, self.maxpool, \
                                            self.layer1, self.layer2, self.layer3, self.layer4, self.avgpool)

        self.fc1 = nn.Linear(self.base_model.fc.in_features, self.base_model.fc.in_features)
        self.activation1 = nn.ReLU()
        self.fc2 = nn.Linear(self.base_model.fc.in_features, self.base_model.fc.in_features)
        self.activation2 = nn.ReLU()
        self.fc3 = nn.Linear(self.base_model.fc.in_features, self.hash_bit)
        self.last_layer = nn.Tanh()
        self.dropout = nn.Dropout(0.5)
        self.hash_layer = nn.Sequential(self.fc1, self.activation1, self.dropout, self.fc2, self.activation2, self.fc3,
                                        self.last_layer)

        self.iter_num = 0
        self.scale = 1

    def forward(self, x):
        x = self.feature_layers(x)
        x = x.view(x.size(0), -1)
        y = self.hash_layer(x)

        #y = self.last_layer(5*y)

        return y

class AlexNetFc(nn.Module):
    def __init__(self, args):
        super(AlexNetFc, self).__init__()

        self.binary = args.binary
        self.base_model = torchvision.models.alexnet(pretrained=True)
        self.features = self.base_model.features
        self.classifier = nn.Sequential()
        for i in range(6):
            self.classifier.add_module("classifier" + str(i), self.base_model.classifier[i])
        self.feature_layers = nn.Sequential(self.features, self.classifier)

        self.hash_bit = args.hash_bit
        feature_dim = self.base_model.classifier[6].in_features
        self.fc1 = nn.Linear(feature_dim, feature_dim)
        self.activation1 = nn.ReLU()
        self.fc2 = nn.Linear(feature_dim, feature_dim)
        self.activation2 = nn.ReLU()
        self.fc3 = nn.Linear(feature_dim, self.hash_bit)
        self.last_layer = nn.Tanh()
        self.dropout = nn.Dropout(0.5)
        self.hash_layer = nn.Sequential(self.fc1, self.activation1, self.fc2, self.activation2, self.fc3,
                                        self.last_layer)
        self.norm = L2N()

    def forward(self, x):

        # alexnet
        print("1", x)
        x = self.features(x)
        print("2", x)
        x = x.view(x.size(0), 256*6*6)
        print("3", x)
        x = self.classifier(x)
        print("4", x)

        # hashlayer
        if self.binary:
            x = self.hash_layer(x)
        else:
            x = self.norm(x)

        print("5", x)

        return x



def freeze_mulit_layers(multi_layers):
    for layer in multi_layers:
        freeze_layer(layer)
def freeze_layer(layer):
    for param in layer.parameters():
        param.requires_grad = False